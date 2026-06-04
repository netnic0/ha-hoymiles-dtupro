"""Data update coordinators for Hoymiles DTU-Pro (D6 + FC3).

Two coordinators share ONE `HoymilesAsyncClient` instance:
  * RealDataCoordinator — short interval (30s default) for live power/voltage/current.
  * MetadataCoordinator — long interval (5min default) for alarm_count, link_status,
    operating_status which rarely change.

The shared client serialises requests internally (asyncio.Lock) so the DTU
sees at most one outstanding Modbus query at a time.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from ha_hoymiles_dtupro import HoymilesAsyncClient, HoymilesError, PlantData

from .const import (
    DEFAULT_SCAN_INTERVAL_METADATA,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import (
        DataUpdateCoordinator,
        UpdateFailed,
    )

_LOGGER = logging.getLogger(__name__)


# Importing HA at module level breaks the PoC's offline tests, so we defer
# to a runtime guard. In production HA always provides these symbols.
try:  # pragma: no cover - exercised only inside HA
    from homeassistant.helpers.update_coordinator import (
        DataUpdateCoordinator,
        UpdateFailed,
    )

    _HAS_HA = True
except ImportError:  # pragma: no cover - PoC offline path
    _HAS_HA = False
    DataUpdateCoordinator = object  # type: ignore[assignment,misc]

    class UpdateFailed(Exception):  # type: ignore[no-redef]
        """Stub used only when running tests outside HA."""


class HoymilesRealDataCoordinator(DataUpdateCoordinator[PlantData]):  # type: ignore[type-arg,misc]
    """Polls live data (PV power, voltages, temperature) at short interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: HoymilesAsyncClient,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL_REAL_DATA,
    ) -> None:
        if not _HAS_HA:  # pragma: no cover - defensive
            raise RuntimeError("HoymilesRealDataCoordinator requires Home Assistant runtime")
        super().__init__(
            hass,
            _LOGGER,
            name="Hoymiles DTU-Pro real data",
            update_interval=update_interval,
            always_update=False,
        )
        self._client = client

    async def _async_update_data(self) -> PlantData:
        try:
            return await self._client.async_get_plant_data()
        except HoymilesError as err:
            raise UpdateFailed(f"Hoymiles real-data fetch failed: {err}") from err


class HoymilesMetadataCoordinator(DataUpdateCoordinator[PlantData]):  # type: ignore[type-arg,misc]
    """Polls slow-changing data (link_status, alarm_count) at long interval.

    Currently fetches the same `PlantData` payload as the real-data coordinator
    because the underlying Modbus query is the same. We keep the split because
    HA entities will subscribe to the appropriate coordinator and we may
    diverge the queries when DTU control endpoints (limit_persistent, etc.)
    are added later.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: HoymilesAsyncClient,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL_METADATA,
    ) -> None:
        if not _HAS_HA:  # pragma: no cover - defensive
            raise RuntimeError("HoymilesMetadataCoordinator requires Home Assistant runtime")
        super().__init__(
            hass,
            _LOGGER,
            name="Hoymiles DTU-Pro metadata",
            update_interval=update_interval,
            always_update=False,
        )
        self._client = client

    async def _async_update_data(self) -> PlantData:
        try:
            return await self._client.async_get_plant_data()
        except HoymilesError as err:
            raise UpdateFailed(f"Hoymiles metadata fetch failed: {err}") from err
