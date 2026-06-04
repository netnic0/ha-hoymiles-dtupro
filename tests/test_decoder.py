"""Tests for the pure binary decoders."""

from __future__ import annotations

import pytest

from ha_hoymiles_dtupro.decoder import (
    apply_data_size_fix,
    decode_inverter_payload,
    decode_serial_number,
)
from ha_hoymiles_dtupro.exceptions import HoymilesDecodeError, HoymilesProtocolError
from ha_hoymiles_dtupro.models import InverterSeries
from tests.fixtures.inverter_samples import (
    SEVEN_HMS_INVERTERS,
    build_inverter_payload,
    build_null_inverter_payload,
    dtu_serial_payload,
)


# ─── decode_serial_number ─────────────────────────────────────────────────────
class TestDecodeSerialNumber:
    def test_returns_uppercase_hex_for_dtu(self) -> None:
        assert decode_serial_number(dtu_serial_payload()) == "AABBCCDDEEFF"

    def test_truncated_buffer_raises(self) -> None:
        with pytest.raises(HoymilesDecodeError, match="6 bytes"):
            decode_serial_number(b"\x00\x01\x02")

    def test_extra_bytes_are_ignored(self) -> None:
        raw = bytes.fromhex("AABBCCDDEEFF") + b"\xde\xad\xbe\xef"
        assert decode_serial_number(raw) == "AABBCCDDEEFF"


# ─── decode_inverter_payload ──────────────────────────────────────────────────
class TestDecodeInverterPayload:
    def test_decodes_all_fields(self) -> None:
        payload = build_inverter_payload(
            serial_hex="1144000000A1",
            port_number=2,
            pv_voltage_v=39.0,
            pv_current_a=8.10,
            grid_voltage_v=234.0,
            grid_frequency_hz=50.00,
            pv_power_w=315.0,
            today_wh=2000,
            total_wh=1_000_000,
            temperature_c=42.0,
            operating_status=1,
            alarm_code=0,
            alarm_count=0,
            link_status=1,
        )
        reading = decode_inverter_payload(payload)
        assert reading.serial_number == "1144000000A1"
        assert reading.port_number == 2
        assert reading.pv_voltage == pytest.approx(39.0)
        assert reading.pv_current == pytest.approx(8.10)
        assert reading.grid_voltage == pytest.approx(234.0)
        assert reading.grid_frequency == pytest.approx(50.00)
        assert reading.pv_power == pytest.approx(315.0)
        assert reading.today_production == 2000
        assert reading.total_production == 1_000_000
        assert reading.temperature == pytest.approx(42.0)
        assert reading.link_status is True
        assert reading.has_alarm is False

    def test_negative_temperature_uses_signed_int16(self) -> None:
        payload = build_inverter_payload(temperature_c=-12.5)
        reading = decode_inverter_payload(payload)
        assert reading.temperature == pytest.approx(-12.5)

    def test_alarm_code_propagates(self) -> None:
        payload = build_inverter_payload(alarm_code=7, alarm_count=3)
        reading = decode_inverter_payload(payload)
        assert reading.has_alarm is True
        assert reading.alarm_code == 7
        assert reading.alarm_count == 3

    def test_link_status_zero_means_offline(self) -> None:
        payload = build_inverter_payload(link_status=0)
        assert decode_inverter_payload(payload).link_status is False

    def test_null_inverter_serial_decodes_to_sentinel(self) -> None:
        payload = build_null_inverter_payload()
        reading = decode_inverter_payload(payload)
        assert reading.serial_number == "000000000000"
        assert reading.series is InverterSeries.UNKNOWN

    def test_truncated_payload_raises(self) -> None:
        truncated = build_inverter_payload()[:30]
        with pytest.raises(HoymilesDecodeError, match="40 bytes"):
            decode_inverter_payload(truncated)

    def test_padded_payload_raises(self) -> None:
        padded = build_inverter_payload() + b"\x00\x00"
        with pytest.raises(HoymilesDecodeError, match="40 bytes"):
            decode_inverter_payload(padded)

    def test_seven_reference_inverters_decode_uniquely(self) -> None:
        """Each fixture payload should decode to a distinct serial."""
        decoded = [decode_inverter_payload(raw) for raw in SEVEN_HMS_INVERTERS]
        assert len({inv.serial_number for inv in decoded}) == 7

    def test_mi_series_uses_correct_current_scale(self) -> None:
        payload = build_inverter_payload(serial_hex="10AABBCCDDEE", pv_current_a=5.55)
        reading = decode_inverter_payload(payload)
        assert reading.series is InverterSeries.MI
        assert reading.pv_current == pytest.approx(5.55)


# ─── apply_data_size_fix ──────────────────────────────────────────────────────
class TestApplyDataSizeFix:
    def test_corrects_first_byte_to_payload_length(self) -> None:
        # Wrong leading byte (0xFF) must be rewritten to actual payload length (3).
        broken = bytes([0xFF, 0xAA, 0xBB, 0xCC])
        fixed = apply_data_size_fix(broken)
        assert fixed == bytes([0x03, 0xAA, 0xBB, 0xCC])

    def test_already_correct_packet_unchanged(self) -> None:
        good = bytes([0x02, 0x12, 0x34])
        assert apply_data_size_fix(good) == good

    def test_empty_packet_raises(self) -> None:
        with pytest.raises(HoymilesProtocolError, match="empty"):
            apply_data_size_fix(b"")

    def test_returns_bytes_not_bytearray(self) -> None:
        out = apply_data_size_fix(bytes([0xFF, 0x01]))
        assert isinstance(out, bytes)
