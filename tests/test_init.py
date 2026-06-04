"""HA-native tests for setup, unload, and reload of the Hoymiles DTU-Pro entry."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hoymiles_dtupro.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.api.models import PlantData


# Patch target for the API client used inside async_setup_entry.
_CLIENT_PATH = "custom_components.hoymiles_dtupro.HoymilesAsyncClient"


@pytest.mark.asyncio
async def test_async_setup_entry_creates_coordinators_and_loads_platforms(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """async_setup_entry stores client + two coordinators in hass.data and loads the platforms."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    bundle = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert bundle["client"] is fake_client
    assert bundle["real_data"].data is mock_plant_data
    assert bundle["metadata"].data is mock_plant_data

    # Both platforms (sensor + binary_sensor) should have at least one entity registered.
    entity_registry_ids = {
        e.entity_id
        for e in hass.states.async_all()
        if e.entity_id.startswith(("sensor.", "binary_sensor."))
    }
    assert any(eid.startswith("sensor.") for eid in entity_registry_ids)
    assert any(eid.startswith("binary_sensor.") for eid in entity_registry_ids)


@pytest.mark.asyncio
async def test_async_unload_entry_clears_hass_data(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Unloading the entry removes its bundle from hass.data[DOMAIN]."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        # Sanity: the entry is stored.
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_async_reload_entry_refreshes_state(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Reloading the entry tears down and brings the integration back up cleanly."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        first_bundle = hass.data[DOMAIN][mock_config_entry.entry_id]

        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        second_bundle = hass.data[DOMAIN][mock_config_entry.entry_id]

    # After reload, the bundle is freshly created — the previous one is gone.
    assert second_bundle is not first_bundle
    assert second_bundle["real_data"].data is mock_plant_data
