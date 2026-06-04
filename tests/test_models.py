"""Tests for the immutable data models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ha_hoymiles_dtupro.models import (
    InverterReading,
    InverterSeries,
    PlantData,
)


def _make_reading(**overrides: object) -> InverterReading:
    """Build an InverterReading with sane defaults, overrideable per test."""
    base: dict[str, object] = {
        "serial_number": "1144000000A1",
        "port_number": 1,
        "pv_voltage": 38.5,
        "pv_current": 8.21,
        "grid_voltage": 233.4,
        "grid_frequency": 50.02,
        "pv_power": 312.6,
        "today_production": 1850,
        "total_production": 985_000,
        "temperature": 41.3,
        "operating_status": 1,
        "alarm_code": 0,
        "alarm_count": 0,
        "link_status": True,
        "data_type": 0,
    }
    base.update(overrides)
    return InverterReading(**base)  # type: ignore[arg-type]


# ─── InverterSeries ───────────────────────────────────────────────────────────
class TestInverterSeries:
    def test_hm_series_detected(self) -> None:
        assert InverterSeries.from_serial("1144000000A1") is InverterSeries.HM

    def test_mi_series_detected(self) -> None:
        assert InverterSeries.from_serial("10AABBCCDDEE") is InverterSeries.MI

    def test_unknown_series_falls_back(self) -> None:
        assert InverterSeries.from_serial("FFAABBCCDDEE") is InverterSeries.UNKNOWN

    def test_empty_serial_does_not_crash(self) -> None:
        assert InverterSeries.from_serial("") is InverterSeries.UNKNOWN

    def test_one_char_serial_does_not_crash(self) -> None:
        assert InverterSeries.from_serial("1") is InverterSeries.UNKNOWN

    def test_enum_values_are_unique(self) -> None:
        # @unique decorator enforces this; the test makes the contract visible.
        values = [member.value for member in InverterSeries]
        assert len(values) == len(set(values))


# ─── InverterReading ──────────────────────────────────────────────────────────
class TestInverterReading:
    def test_post_init_validates_serial_length(self) -> None:
        with pytest.raises(ValueError, match="serial_number must be 12 chars"):
            _make_reading(serial_number="TOO_SHORT")

    def test_post_init_validates_port_number_range(self) -> None:
        with pytest.raises(ValueError, match="port_number"):
            _make_reading(port_number=999)

    def test_post_init_rejects_negative_pv_power(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            _make_reading(pv_power=-1.0)

    def test_post_init_rejects_negative_production(self) -> None:
        with pytest.raises(ValueError, match="counters cannot be negative"):
            _make_reading(today_production=-5)

    def test_frozen_dataclass_is_immutable(self) -> None:
        reading = _make_reading()
        # FrozenInstanceError is a subclass of AttributeError; either is acceptable.
        with pytest.raises(AttributeError):
            reading.pv_power = 999.0  # type: ignore[misc]

    def test_series_property_uses_serial_prefix(self) -> None:
        assert _make_reading(serial_number="1144AABBCCDD").series is InverterSeries.HM
        assert _make_reading(serial_number="10AABBCCDDEE").series is InverterSeries.MI

    def test_has_alarm_false_when_alarm_code_zero(self) -> None:
        assert _make_reading(alarm_code=0).has_alarm is False

    def test_has_alarm_true_when_alarm_code_nonzero(self) -> None:
        assert _make_reading(alarm_code=42).has_alarm is True


# ─── PlantData ────────────────────────────────────────────────────────────────
class TestPlantData:
    def test_post_init_rejects_empty_dtu_serial(self) -> None:
        with pytest.raises(ValueError, match="dtu_serial cannot be empty"):
            PlantData(dtu_serial="")

    def test_default_fetched_at_is_recent(self) -> None:
        plant = PlantData(dtu_serial="AABBCCDDEEFF")
        delta = datetime.now(UTC) - plant.fetched_at
        assert delta < timedelta(seconds=1)

    def test_default_inverters_is_empty_tuple(self) -> None:
        plant = PlantData(dtu_serial="AABBCCDDEEFF")
        assert plant.inverters == ()
        assert plant.inverter_count == 0

    def test_aggregations_skip_offline_inverters(self) -> None:
        online = _make_reading(
            serial_number="1144000000A1",
            pv_power=300.0,
            today_production=1000,
            total_production=50000,
            link_status=True,
        )
        offline = _make_reading(
            serial_number="1144000000A2",
            pv_power=999.0,
            today_production=9999,
            total_production=999_999,
            link_status=False,
        )
        plant = PlantData(dtu_serial="AABBCCDDEEFF", inverters=(online, offline))

        assert plant.online_inverters == (online,)
        assert plant.pv_power == 300.0
        assert plant.today_production == 1000
        assert plant.total_production == 50000

    def test_alarm_flag_true_if_any_online_inverter_has_alarm(self) -> None:
        normal = _make_reading(serial_number="1144000000A1", alarm_code=0)
        alarming = _make_reading(serial_number="1144000000A2", alarm_code=12)
        plant = PlantData(dtu_serial="AABBCCDDEEFF", inverters=(normal, alarming))
        assert plant.alarm_flag is True

    def test_alarm_flag_ignores_offline_inverter_with_stale_alarm(self) -> None:
        offline_alarming = _make_reading(
            serial_number="1144000000A2", alarm_code=99, link_status=False
        )
        plant = PlantData(dtu_serial="AABBCCDDEEFF", inverters=(offline_alarming,))
        assert plant.alarm_flag is False
