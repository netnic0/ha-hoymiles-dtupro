"""HA-native tests for the Hoymiles DTU-Pro binary_sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hoymiles_dtupro.binary_sensor import (
    HoymilesAlarmBinarySensor,
    HoymilesLinkBinarySensor,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.api.models import PlantData


_CLIENT_PATH = "custom_components.hoymiles_dtupro.api.HoymilesAsyncClient"


@pytest.mark.asyncio
async def test_setup_creates_alarm_and_link_binary_sensors(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """One alarm binary_sensor for the plant + one link binary_sensor per inverter."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    binary_ids = [
        s.entity_id for s in hass.states.async_all() if s.entity_id.startswith("binary_sensor.")
    ]
    # 1 alarm (plant-level) + 1 link per inverter.
    expected = 1 + mock_plant_data.inverter_count
    assert len(binary_ids) == expected


def test_alarm_binary_sensor_is_on_when_plant_alarm_flag_true(
    mock_plant_data: PlantData,
) -> None:
    """The plant-level alarm binary_sensor mirrors PlantData.alarm_flag."""
    # Build a plant snapshot with one inverter raising alarm_code != 0 to flip alarm_flag.
    from dataclasses import replace

    from custom_components.hoymiles_dtupro.api.models import PlantData

    alarming_inverters = (
        replace(mock_plant_data.inverters[0], alarm_code=99, alarm_count=1),
        *mock_plant_data.inverters[1:],
    )
    alarming_plant = PlantData(
        dtu_serial=mock_plant_data.dtu_serial,
        fetched_at=mock_plant_data.fetched_at,
        inverters=alarming_inverters,
    )
    assert alarming_plant.alarm_flag is True

    coord = AsyncMock()
    coord.data = alarming_plant
    sensor = HoymilesAlarmBinarySensor.__new__(HoymilesAlarmBinarySensor)
    sensor.coordinator = coord
    assert sensor.is_on is True

    # And False when the original (no-alarm) snapshot is used.
    coord.data = mock_plant_data
    assert sensor.is_on is False


def test_link_binary_sensor_reflects_inverter_link_status(
    mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """The per-inverter link sensor reads link_status from the matching inverter."""
    target_serial = mock_inverter_serials[3]
    coord = AsyncMock()
    coord.data = mock_plant_data

    sensor = HoymilesLinkBinarySensor.__new__(HoymilesLinkBinarySensor)
    sensor.coordinator = coord
    sensor._inverter_serial = target_serial

    expected_inv = next(
        inv for inv in mock_plant_data.inverters if inv.serial_number == target_serial
    )
    assert sensor.is_on is expected_inv.link_status

    # Unknown serial → default False (RF link absent).
    sensor._inverter_serial = "ZZZZZZZZZZZZ"
    assert sensor.is_on is False
