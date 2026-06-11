"""HA-native tests for the Hoymiles DTU-Pro diagnostics platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hoymiles_dtupro.const import DOMAIN
from custom_components.hoymiles_dtupro.diagnostics import (
    REDACT_KEYS,
    async_get_config_entry_diagnostics,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.api.models import PlantData


_CLIENT_PATH = "custom_components.hoymiles_dtupro.api.HoymilesAsyncClient"


@pytest.mark.asyncio
async def test_diagnostics_redacts_dtu_serial_and_host(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Diagnostics dump must never reveal the DTU serial, host, or per-inverter serials."""
    mock_config_entry.add_to_hass(hass)
    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        payload = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # The contract: REDACT_KEYS lists the fields that must be redacted.
    assert "host" in REDACT_KEYS
    assert "dtu_serial" in REDACT_KEYS
    assert "serial_number" in REDACT_KEYS

    # Original sensitive values must not be present anywhere in the dumped payload string.
    serialised = repr(payload)
    assert mock_plant_data.dtu_serial not in serialised
    for inv in mock_plant_data.inverters:
        assert inv.serial_number not in serialised
    # The host saved on the config entry data also must not be leaked.
    assert mock_config_entry.data["host"] not in serialised


@pytest.mark.asyncio
async def test_diagnostics_includes_real_data_and_metadata_snapshots(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Both coordinator snapshots show up in the diagnostics dump (after redaction)."""
    mock_config_entry.add_to_hass(hass)
    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        payload = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert "real_data" in payload
    assert "metadata" in payload
    # Each snapshot should report the inverter count even after dtu_serial is redacted.
    assert payload["real_data"]["inverter_count"] == mock_plant_data.inverter_count
    assert payload["metadata"]["inverter_count"] == mock_plant_data.inverter_count
    # And aggregate fields that are not redacted.
    assert payload["real_data"]["pv_power"] == pytest.approx(mock_plant_data.pv_power)


@pytest.mark.asyncio
async def test_diagnostics_handles_coordinator_with_no_data(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """If a coordinator has not refreshed yet, its slot is None — not a crash."""
    mock_config_entry.add_to_hass(hass)
    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Force the metadata coordinator to drop its data after setup.
        bundle = hass.data[DOMAIN][mock_config_entry.entry_id]
        bundle["metadata"].data = None

        payload = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert payload["real_data"] is not None
    assert payload["metadata"] is None


@pytest.mark.asyncio
async def test_diagnostics_includes_coordinator_state(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Diagnostics expose runtime health (last update, intervals, online count)."""
    mock_config_entry.add_to_hass(hass)
    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        payload = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    coord_state = payload.get("coordinator_state")
    assert coord_state is not None, "coordinator_state section must be present"

    for slot in ("real_data", "metadata"):
        section = coord_state[slot]
        assert section["last_update_success"] is True
        # ISO-formatted timestamp string after a successful first refresh.
        assert isinstance(section["last_update_success_time"], str)
        assert section["last_update_success_time"].endswith("+00:00")
        # Update intervals are positive numbers reflecting the runtime values.
        assert section["update_interval_seconds"] > 0
        # Online inverter count agrees with the snapshot (every inv is online by default).
        assert section["online_inverter_count"] == len(mock_plant_data.online_inverters)
        assert section["inverter_count"] == mock_plant_data.inverter_count
