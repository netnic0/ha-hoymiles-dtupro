"""Hoymiles DTU-Pro — Home Assistant integration entry point.

This is the SKELETON of the modern integration; the actual entity wiring will
be fleshed out in Milestones M1-M2 (see PLAN_NOUVELLE_INTEGRATION.md).

Architecture (D5):
    Layer 1 (HA)        ← this package + sensor.py + config_flow.py
    Layer 2 (Coordinator) ← coordinator.py — TWO coordinators sharing ONE client (FC3)
    Layer 3 (API)       ← `ha_hoymiles_dtupro` (sibling library, pure async, no HA imports)
    Layer 4 (Models)    ← dataclasses inside ha_hoymiles_dtupro.models
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ha_hoymiles_dtupro import HoymilesAsyncClient

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    DOMAIN,
)
from .coordinator import HoymilesMetadataCoordinator, HoymilesRealDataCoordinator

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hoymiles DTU-Pro from a config entry."""
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

    No migrations needed for v1 yet. Stub kept for forward-compat (mirrors
    suaveolent F1 pattern from REVUE_SUAVEOLENT_ET_POC.md).
    """
    _LOGGER.debug("No migration needed for entry %s (version=%s)", entry.entry_id, entry.version)
    return True
