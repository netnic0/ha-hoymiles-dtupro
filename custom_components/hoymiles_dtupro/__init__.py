"""Hoymiles DTU-Pro — Home Assistant integration entry point.

Architecture (D5):
    Layer 1 (HA)        ← this package + sensor.py + config_flow.py
    Layer 2 (Coordinator) ← coordinator.py — TWO coordinators sharing ONE client (FC3)
    Layer 3 (API)       ← `.api` (sub-package, pure async, no HA imports)
    Layer 4 (Models)    ← dataclasses inside .api.models

The top-level imports are kept HA-free so this package can be partially imported
(e.g. `custom_components.hoymiles_dtupro.api.const`) by tools and tests that do
not have a Home Assistant runtime available. HA-only imports (coordinator,
config flow registration) happen lazily inside `async_setup_entry`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hoymiles DTU-Pro from a config entry."""
    # Lazy imports: keep the package importable in non-HA environments (e.g. tooling
    # that only inspects .api.const). HA itself is always present at this call site.
    from .api import HoymilesAsyncClient
    from .coordinator import HoymilesMetadataCoordinator, HoymilesRealDataCoordinator

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 502)
    unit_id = entry.data.get(CONF_UNIT_ID, 1)

    # FC3: ONE shared client across both coordinators.
    client = HoymilesAsyncClient(host=host, port=port, unit_id=unit_id)

    real_data_coord = HoymilesRealDataCoordinator(hass, client)
    metadata_coord = HoymilesMetadataCoordinator(hass, client)

    # Force initial fetches (raises ConfigEntryNotReady on failure).
    await real_data_coord.async_config_entry_first_refresh()
    await metadata_coord.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "real_data": real_data_coord,
        "metadata": metadata_coord,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry data to the current schema.

    No migrations needed for v1 yet. Stub kept for forward-compat.
    """
    _LOGGER.debug("No migration needed for entry %s (version=%s)", entry.entry_id, entry.version)
    return True
