"""HA-native tests for the Hoymiles DTU-Pro sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hoymiles_dtupro.sensor import (
    INVERTER_SENSORS,
    PLANT_SENSORS,
    HoymilesInverterSensor,
    HoymilesPlantSensor,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.api.models import PlantData


_CLIENT_PATH = "custom_components.hoymiles_dtupro.api.HoymilesAsyncClient"


@pytest.mark.asyncio
async def test_setup_creates_plant_and_inverter_sensors(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Setting up the entry registers plant + per-inverter sensor entities.

    Expected count: len(PLANT_SENSORS) + n_inverters * len(INVERTER_SENSORS).
    """
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    sensor_entity_ids = [
        s.entity_id for s in hass.states.async_all() if s.entity_id.startswith("sensor.")
    ]
    expected_count = len(PLANT_SENSORS) + mock_plant_data.inverter_count * len(INVERTER_SENSORS)
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

    # Plant.pv_power is the sum across online inverters; each fixture inverter is online @ 312.6 W.
    expected = sum(inv.pv_power for inv in mock_plant_data.inverters if inv.link_status)
    assert sensor.native_value == pytest.approx(expected)


def test_inverter_sensor_native_value_resolves_by_serial(
    mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """Per-inverter sensor's native_value pulls from the inverter matching its serial."""
    target_serial = mock_inverter_serials[2]  # arbitrary inverter
    description = next(d for d in INVERTER_SENSORS if d.key == "temperature")

    coord = AsyncMock()
    coord.data = mock_plant_data

    sensor = HoymilesInverterSensor.__new__(HoymilesInverterSensor)
    sensor.coordinator = coord
    sensor.entity_description = description
    sensor._inverter_serial = target_serial

    # All fixture inverters share the same temperature (41.3 °C); we verify lookup not mismatch.
    expected_inv = next(
        inv for inv in mock_plant_data.inverters if inv.serial_number == target_serial
    )
    assert sensor.native_value == pytest.approx(expected_inv.temperature)


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
