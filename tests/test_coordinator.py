"""HA-native tests for the Hoymiles DTU-Pro coordinators.

Validates:
  * First refresh populates `coordinator.data` with the PlantData snapshot.
  * UpdateFailed is raised on HoymilesError (so HA retries with backoff).
  * Real-data and metadata coordinators share ONE underlying client (FC3).
  * Each coordinator's update_interval matches its declared default.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from custom_components.hoymiles_dtupro.api.client import HoymilesAsyncClient
from custom_components.hoymiles_dtupro.api.exceptions import HoymilesConnectionError
from custom_components.hoymiles_dtupro.const import (
    DEFAULT_SCAN_INTERVAL_METADATA,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
)
from custom_components.hoymiles_dtupro.coordinator import (
    HoymilesMetadataCoordinator,
    HoymilesRealDataCoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.hoymiles_dtupro.api.models import PlantData


@pytest.mark.asyncio
async def test_real_data_coordinator_first_refresh_populates_data(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """A successful first refresh stores the PlantData snapshot on the coordinator."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    coord = HoymilesRealDataCoordinator(hass, client)
    await coord.async_config_entry_first_refresh()

    assert coord.data is mock_plant_data
    client.async_get_plant_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_real_data_coordinator_raises_update_failed_on_hoymiles_error(
    hass: HomeAssistant,
) -> None:
    """A HoymilesError from the client must surface as UpdateFailed for HA backoff."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(side_effect=HoymilesConnectionError("nope"))

    coord = HoymilesRealDataCoordinator(hass, client)
    with pytest.raises(UpdateFailed, match="real-data fetch failed"):
        await coord._async_update_data()


@pytest.mark.asyncio
async def test_real_data_and_metadata_share_one_client(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """FC3: a single client instance drives both coordinators (no duplicate sockets)."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    real = HoymilesRealDataCoordinator(hass, client)
    meta = HoymilesMetadataCoordinator(hass, client)

    await real.async_config_entry_first_refresh()
    await meta.async_config_entry_first_refresh()

    # Same underlying client object — proves the FC3 sharing contract.
    assert real._client is meta._client is client
    # Each coordinator made one fetch on the shared client.
    assert client.async_get_plant_data.await_count == 2


@pytest.mark.asyncio
async def test_coordinators_use_their_default_intervals(hass: HomeAssistant) -> None:
    """The two coordinators carry the documented default intervals (30s vs 5min)."""
    client = AsyncMock(spec=HoymilesAsyncClient)

    real = HoymilesRealDataCoordinator(hass, client)
    meta = HoymilesMetadataCoordinator(hass, client)

    assert real.update_interval == DEFAULT_SCAN_INTERVAL_REAL_DATA == timedelta(seconds=30)
    assert meta.update_interval == DEFAULT_SCAN_INTERVAL_METADATA == timedelta(minutes=5)
    # Sanity: the real-data interval is strictly shorter than the metadata interval.
    assert real.update_interval < meta.update_interval
