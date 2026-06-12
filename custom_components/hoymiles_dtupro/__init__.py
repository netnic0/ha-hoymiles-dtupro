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
from datetime import timedelta
from typing import TYPE_CHECKING

from .const import (
    CONF_BACKOFF_INITIAL_S,
    CONF_BACKOFF_MAX_S,
    CONF_CO2_FACTOR_KG_PER_KWH,
    CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
    CONF_HOST,
    CONF_INVERTER_OFFLINE_THRESHOLD_H,
    CONF_PORT,
    CONF_RETRY_ATTEMPTS,
    CONF_SCAN_INTERVAL_METADATA,
    CONF_SCAN_INTERVAL_REAL_DATA,
    CONF_TIMEOUT_S,
    CONF_TREE_KG_CO2_PER_YEAR,
    CONF_UNIT_ID,
    DEFAULT_BACKOFF_INITIAL_S,
    DEFAULT_BACKOFF_MAX_S,
    DEFAULT_CO2_FACTOR_KG_PER_KWH,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_SCAN_INTERVAL_METADATA,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
    DEFAULT_TIMEOUT_S,
    DEFAULT_TREE_KG_CO2_PER_YEAR,
    DOMAIN,
    ISSUE_DTU_UNREACHABLE_THRESHOLD,
    ISSUE_INVERTER_OFFLINE_THRESHOLD,
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

    # ─── entry.data — connection identity (host/port/unit_id only) ─────────
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 502)
    unit_id = entry.data.get(CONF_UNIT_ID, 1)

    # ─── entry.options — user-tunable knobs (PR #4) ────────────────────────
    options = entry.options
    timeout_s = float(options.get(CONF_TIMEOUT_S, DEFAULT_TIMEOUT_S))
    retry_attempts = int(options.get(CONF_RETRY_ATTEMPTS, DEFAULT_RETRY_ATTEMPTS))
    backoff_initial_s = float(options.get(CONF_BACKOFF_INITIAL_S, DEFAULT_BACKOFF_INITIAL_S))
    backoff_max_s = float(options.get(CONF_BACKOFF_MAX_S, DEFAULT_BACKOFF_MAX_S))

    real_data_interval = timedelta(
        seconds=int(
            options.get(
                CONF_SCAN_INTERVAL_REAL_DATA,
                DEFAULT_SCAN_INTERVAL_REAL_DATA.total_seconds(),
            )
        )
    )
    metadata_interval = timedelta(
        seconds=int(
            options.get(
                CONF_SCAN_INTERVAL_METADATA,
                DEFAULT_SCAN_INTERVAL_METADATA.total_seconds(),
            )
        )
    )
    dtu_unreachable_threshold = timedelta(
        minutes=int(
            options.get(
                CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
                ISSUE_DTU_UNREACHABLE_THRESHOLD.total_seconds() // 60,
            )
        )
    )
    inverter_offline_threshold = timedelta(
        hours=int(
            options.get(
                CONF_INVERTER_OFFLINE_THRESHOLD_H,
                ISSUE_INVERTER_OFFLINE_THRESHOLD.total_seconds() // 3600,
            )
        )
    )

    # FC3: ONE shared client across both coordinators.
    client = HoymilesAsyncClient(
        host=host,
        port=port,
        unit_id=unit_id,
        timeout=timeout_s,
        retry_attempts=retry_attempts,
        backoff_initial_s=backoff_initial_s,
        backoff_max_s=backoff_max_s,
    )

    real_data_coord = HoymilesRealDataCoordinator(
        hass,
        client,
        entry_id=entry.entry_id,
        host=host,
        update_interval=real_data_interval,
        dtu_unreachable_threshold=dtu_unreachable_threshold,
    )
    metadata_coord = HoymilesMetadataCoordinator(
        hass,
        client,
        entry_id=entry.entry_id,
        update_interval=metadata_interval,
        inverter_offline_threshold=inverter_offline_threshold,
    )

    # Force initial fetches (raises ConfigEntryNotReady on failure).
    await real_data_coord.async_config_entry_first_refresh()
    await metadata_coord.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "real_data": real_data_coord,
        "metadata": metadata_coord,
    }

    # Reload the entry whenever the user submits OptionsFlow changes.
    entry.async_on_unload(entry.add_update_listener(_async_options_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when the user changes options.

    HA fires this listener immediately after `OptionsFlow.async_create_entry`
    returns. The reload tears down the coordinators and the client, then calls
    `async_setup_entry` again — which re-reads `entry.options` and applies the
    new values.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Cleanup of Repair Issues created by the coordinators: even though
    `is_persistent=False` issues are dropped at HA restart, an integration
    *reload* (no full HA restart) would otherwise leave stale issues visible.
    """
    from homeassistant.helpers import issue_registry as ir

    from .const import ISSUE_ID_DTU_UNREACHABLE, ISSUE_ID_INVERTER_OFFLINE

    bundle = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if bundle is not None:
        # Clear the per-DTU unreachable issue.
        ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_ID_DTU_UNREACHABLE}_{entry.entry_id}")
        # Clear every per-inverter offline issue that this metadata coordinator
        # ever raised (or could have raised) for this entry.
        metadata_coord = bundle.get("metadata")
        if metadata_coord is not None:
            for serial in metadata_coord.known_inverter_serials:
                ir.async_delete_issue(
                    hass,
                    DOMAIN,
                    f"{ISSUE_ID_INVERTER_OFFLINE}_{serial}_{entry.entry_id}",
                )

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry data to the current schema.

    Migration history:
      * 1.1 → 1.2 (PR #4): move `scan_interval_real_data` from `entry.data`
        to `entry.options`. The key was previously collected by the user step
        but never consumed by `async_setup_entry` (latent bug), so existing
        users see no behavior change beyond the value finally being honoured.
      * 1.2 → 1.3 (PR #6c): inject default `co2_factor_kg_per_kwh` and
        `tree_kg_co2_per_year` into `entry.options` so the new environmental
        impact sensors can read them without requiring the user to walk
        through the OptionsFlow.

    The two branches below are INDEPENDENT `if` blocks (NOT chained `elif`)
    so that an entry created in v1.0 (minor_version=1) traverses both
    migrations within a single call: first to v1.2, then to v1.3.
    """
    _LOGGER.debug(
        "Checking migration for entry %s (version=%s minor=%s)",
        entry.entry_id,
        entry.version,
        entry.minor_version,
    )

    if entry.version == 1 and entry.minor_version < 2:
        new_data = dict(entry.data)
        new_options = dict(entry.options)

        scan_interval = new_data.pop(CONF_SCAN_INTERVAL_REAL_DATA, None)
        if scan_interval is not None and CONF_SCAN_INTERVAL_REAL_DATA not in new_options:
            new_options[CONF_SCAN_INTERVAL_REAL_DATA] = scan_interval

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            options=new_options,
            minor_version=2,
            version=1,
        )
        _LOGGER.info(
            "Migrated Hoymiles DTU-Pro entry %s to v1.2 (scan_interval_real_data moved to options)",
            entry.entry_id,
        )

    if entry.version == 1 and entry.minor_version == 2:
        new_options = dict(entry.options)
        new_options.setdefault(CONF_CO2_FACTOR_KG_PER_KWH, DEFAULT_CO2_FACTOR_KG_PER_KWH)
        new_options.setdefault(CONF_TREE_KG_CO2_PER_YEAR, DEFAULT_TREE_KG_CO2_PER_YEAR)

        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
            minor_version=3,
            version=1,
        )
        _LOGGER.info(
            "Migrated Hoymiles DTU-Pro entry %s to v1.3 (added CO2/tree factor defaults)",
            entry.entry_id,
        )

    return True
