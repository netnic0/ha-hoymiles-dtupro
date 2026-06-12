"""HA-native tests for the Hoymiles DTU-Pro sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.entity import EntityCategory

from custom_components.hoymiles_dtupro.sensor import (
    INVERTER_SENSORS,
    PLANT_ENVIRONMENTAL_SENSORS,
    PLANT_SENSORS,
    PORT_SENSORS,
    HoymilesInverterPortSensor,
    HoymilesInverterSensor,
    HoymilesPlantSensor,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.api.models import PlantData


_CLIENT_PATH = "custom_components.hoymiles_dtupro.api.HoymilesAsyncClient"

# 7 inverters, 2 ports each -> 14 InverterReading objects.
_N_INVERTERS = 7
_N_PORTS = 2


@pytest.mark.asyncio
async def test_setup_creates_correct_sensor_count(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Sensor count: (3 plant + 2 environmental) + N_inv*5 inverter + N_inv*N_ports*5 port."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    sensor_entity_ids = [
        s.entity_id for s in hass.states.async_all() if s.entity_id.startswith("sensor.")
    ]
    expected_count = (
        len(PLANT_SENSORS)
        + len(PLANT_ENVIRONMENTAL_SENSORS)
        + _N_INVERTERS * len(INVERTER_SENSORS)
        + _N_INVERTERS * _N_PORTS * len(PORT_SENSORS)
    )
    assert len(sensor_entity_ids) == expected_count


def test_plant_sensor_native_value_pulls_from_coordinator(
    mock_plant_data: PlantData,
) -> None:
    """Plant-level sensor's native_value reads the matching attribute from PlantData."""
    coord = AsyncMock()
    coord.data = mock_plant_data

    description = next(d for d in PLANT_SENSORS if d.key == "pv_power")
    sensor = HoymilesPlantSensor.__new__(HoymilesPlantSensor)
    sensor.coordinator = coord
    sensor.entity_description = description

    expected = sum(inv.pv_power for inv in mock_plant_data.inverters if inv.link_status)
    assert sensor.native_value == pytest.approx(expected)


def test_inverter_sensor_reads_port1(
    mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """Per-inverter sensor reads from port_number == 1 for temperature."""
    target_serial = mock_inverter_serials[2]
    description = next(d for d in INVERTER_SENSORS if d.key == "temperature")

    coord = AsyncMock()
    coord.data = mock_plant_data

    sensor = HoymilesInverterSensor.__new__(HoymilesInverterSensor)
    sensor.coordinator = coord
    sensor.entity_description = description
    sensor._inverter_serial = target_serial

    port1 = next(
        inv
        for inv in mock_plant_data.inverters
        if inv.serial_number == target_serial and inv.port_number == 1
    )
    assert sensor.native_value == pytest.approx(port1.temperature)


def test_inverter_sensor_returns_none_for_unknown_serial(
    mock_plant_data: PlantData,
) -> None:
    """If the configured serial is not in the plant snapshot, native_value is None."""
    description = next(d for d in INVERTER_SENSORS if d.key == "temperature")

    coord = AsyncMock()
    coord.data = mock_plant_data

    sensor = HoymilesInverterSensor.__new__(HoymilesInverterSensor)
    sensor.coordinator = coord
    sensor.entity_description = description
    sensor._inverter_serial = "ZZZZZZZZZZZZ"

    assert sensor.native_value is None


def test_port_sensor_resolves_correct_port(
    mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """Port sensor native_value resolves by both serial and port_number."""
    target_serial = mock_inverter_serials[1]
    description = next(d for d in PORT_SENSORS if d.key == "pv_power")

    coord = AsyncMock()
    coord.data = mock_plant_data

    for port in (1, 2):
        sensor = HoymilesInverterPortSensor.__new__(HoymilesInverterPortSensor)
        sensor.coordinator = coord
        sensor.entity_description = description
        sensor._inverter_serial = target_serial
        sensor._port_number = port

        expected = next(
            inv.pv_power
            for inv in mock_plant_data.inverters
            if inv.serial_number == target_serial and inv.port_number == port
        )
        assert sensor.native_value == pytest.approx(expected)


def test_port_sensor_returns_none_for_unknown_serial(
    mock_plant_data: PlantData,
) -> None:
    """Port sensor returns None when serial is not found."""
    description = next(d for d in PORT_SENSORS if d.key == "pv_voltage")

    coord = AsyncMock()
    coord.data = mock_plant_data

    sensor = HoymilesInverterPortSensor.__new__(HoymilesInverterPortSensor)
    sensor.coordinator = coord
    sensor.entity_description = description
    sensor._inverter_serial = "ZZZZZZZZZZZZ"
    sensor._port_number = 1

    assert sensor.native_value is None


# ─────────────────────────────────────────────────────────────────────────────
# Descriptor-level assertions: lock down state_class, suggested_unit_of_measurement
# and entity_category so future refactors of the SensorEntityDescription tuples
# cannot regress the Energy-Dashboard semantics or the Diagnostics categorisation.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("sensors", "key"),
    [
        (PLANT_SENSORS, "today_production"),
        (PLANT_SENSORS, "total_production"),
        (PORT_SENSORS, "today_production"),
        (PORT_SENSORS, "total_production"),
    ],
)
def test_energy_sensors_suggest_kwh_display(sensors, key) -> None:
    """Energy sensors store in Wh but suggest kWh for display readability."""
    desc = next(d for d in sensors if d.key == key)
    assert desc.native_unit_of_measurement == UnitOfEnergy.WATT_HOUR
    assert desc.suggested_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR


@pytest.mark.parametrize("sensors", [PLANT_SENSORS, PORT_SENSORS])
def test_total_production_uses_state_class_total(sensors) -> None:
    """`total_production` keeps state_class TOTAL (not TOTAL_INCREASING).

    The Hoymiles DTU resets the per-port lifetime counter at midnight, which
    would trigger HA recorder warnings with TOTAL_INCREASING. See commit 13b3a13.
    """
    desc = next(d for d in sensors if d.key == "total_production")
    assert desc.state_class == SensorStateClass.TOTAL


@pytest.mark.parametrize("sensors", [PLANT_SENSORS, PORT_SENSORS])
def test_today_production_uses_total_increasing(sensors) -> None:
    """`today_production` resets at midnight (intentional) — TOTAL_INCREASING fits."""
    desc = next(d for d in sensors if d.key == "today_production")
    assert desc.state_class == SensorStateClass.TOTAL_INCREASING


@pytest.mark.parametrize("key", ["alarm_code", "alarm_count"])
def test_alarm_sensors_are_diagnostic(key) -> None:
    """Alarm entities are operational diagnostics, hidden from main entity list."""
    desc = next(d for d in INVERTER_SENSORS if d.key == key)
    assert desc.entity_category == EntityCategory.DIAGNOSTIC


def test_no_unexpected_diagnostic_categorisation() -> None:
    """Only the alarm sensors should be marked DIAGNOSTIC — not energy or power."""
    diagnostic_keys = {
        d.key
        for sensors in (PLANT_SENSORS, PLANT_ENVIRONMENTAL_SENSORS, INVERTER_SENSORS, PORT_SENSORS)
        for d in sensors
        if d.entity_category == EntityCategory.DIAGNOSTIC
    }
    assert diagnostic_keys == {"alarm_code", "alarm_count"}
