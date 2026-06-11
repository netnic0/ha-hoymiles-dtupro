"""Constants for the Hoymiles DTU-Pro Home Assistant integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "hoymiles_dtupro"
"""HA integration domain. Distinct from legacy `hoymiles_dtu` (D1)."""

# ─── Config flow keys ─────────────────────────────────────────────────────────
CONF_HOST: Final[str] = "host"
CONF_PORT: Final[str] = "port"
CONF_UNIT_ID: Final[str] = "unit_id"
CONF_SCAN_INTERVAL_REAL_DATA: Final[str] = "scan_interval_real_data"
CONF_SCAN_INTERVAL_METADATA: Final[str] = "scan_interval_metadata"

# ─── Default polling intervals (D6 — multi-coordinator) ────────────────────────
DEFAULT_SCAN_INTERVAL_REAL_DATA: Final[timedelta] = timedelta(seconds=60)
"""Live data: pv_power, voltages, temperature."""

DEFAULT_SCAN_INTERVAL_METADATA: Final[timedelta] = timedelta(minutes=5)
"""Metadata: link_status, alarm_count, operating_status (rarely changes)."""

MIN_SCAN_INTERVAL_SECONDS: Final[int] = 10
"""Lower bound enforced by the config flow to avoid hammering the DTU."""

# ─── Repair Issue thresholds (PR #2) ──────────────────────────────────────────
# Hardcoded for now; PR #4 (OptionsFlow) will make them user-configurable.

ISSUE_DTU_UNREACHABLE_THRESHOLD: Final[timedelta] = timedelta(minutes=5)
"""How long the DTU must be unreachable before raising `dtu_unreachable`."""

ISSUE_INVERTER_OFFLINE_THRESHOLD: Final[timedelta] = timedelta(hours=6)
"""How long an inverter must report `link_status=False` before raising
`inverter_offline_long`. Only counts AFTER the inverter has been seen online
at least once since the integration started — never fires for new hardware
that has yet to come online for the first time."""

ISSUE_ID_DTU_UNREACHABLE: Final[str] = "dtu_unreachable"
"""Repair issue ID prefix; final ID is `f"{prefix}_{entry.entry_id}"`."""

ISSUE_ID_INVERTER_OFFLINE: Final[str] = "inverter_offline"
"""Repair issue ID prefix; final ID is `f"{prefix}_{serial}_{entry.entry_id}"`."""

# ─── Logger names declared in manifest.json ───────────────────────────────────
LOGGER_NAME: Final[str] = f"custom_components.{DOMAIN}"
