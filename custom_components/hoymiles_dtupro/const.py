"""Constants for the Hoymiles DTU-Pro Home Assistant integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

# Re-export client-construction defaults from the pure api package so the HA
# layer can wire them into entry.options without duplicating the values.
from .api.const import (
    DEFAULT_BACKOFF_INITIAL_S,
    DEFAULT_BACKOFF_MAX_S,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT_S,
)

DOMAIN: Final[str] = "hoymiles_dtupro"
"""HA integration domain. Distinct from legacy `hoymiles_dtu` (D1)."""

# ─── Config flow keys (entry.data — host/port/unit_id only after PR #4) ───────
CONF_HOST: Final[str] = "host"
CONF_PORT: Final[str] = "port"
CONF_UNIT_ID: Final[str] = "unit_id"

# ─── Options flow keys (entry.options — added in PR #4) ───────────────────────
CONF_SCAN_INTERVAL_REAL_DATA: Final[str] = "scan_interval_real_data"
CONF_SCAN_INTERVAL_METADATA: Final[str] = "scan_interval_metadata"
CONF_TIMEOUT_S: Final[str] = "timeout_s"
CONF_RETRY_ATTEMPTS: Final[str] = "retry_attempts"
CONF_BACKOFF_INITIAL_S: Final[str] = "backoff_initial_s"
CONF_BACKOFF_MAX_S: Final[str] = "backoff_max_s"
CONF_DTU_UNREACHABLE_THRESHOLD_MIN: Final[str] = "dtu_unreachable_threshold_min"
CONF_INVERTER_OFFLINE_THRESHOLD_H: Final[str] = "inverter_offline_threshold_h"

# ─── Environmental impact knobs (entry.options — added in PR #6c) ──────────────
CONF_CO2_FACTOR_KG_PER_KWH: Final[str] = "co2_factor_kg_per_kwh"
"""User-configurable CO2 emission factor (kg CO2 avoided per kWh produced)."""

CONF_TREE_KG_CO2_PER_YEAR: Final[str] = "tree_kg_co2_per_year"
"""User-configurable CO2 absorbed per young planted tree per year (kg)."""

# ─── Default polling intervals (D6 — multi-coordinator) ────────────────────────
DEFAULT_SCAN_INTERVAL_REAL_DATA: Final[timedelta] = timedelta(seconds=60)
"""Live data: pv_power, voltages, temperature."""

DEFAULT_SCAN_INTERVAL_METADATA: Final[timedelta] = timedelta(minutes=5)
"""Metadata: link_status, alarm_count, operating_status (rarely changes)."""

MIN_SCAN_INTERVAL_SECONDS: Final[int] = 10
"""Lower bound enforced by the config flow to avoid hammering the DTU."""

# ─── OptionsFlow voluptuous range bounds (PR #4) ──────────────────────────────
OPTIONS_SCAN_INTERVAL_REAL_DATA_MIN: Final[int] = 10
OPTIONS_SCAN_INTERVAL_REAL_DATA_MAX: Final[int] = 600
OPTIONS_SCAN_INTERVAL_METADATA_MIN: Final[int] = 60
OPTIONS_SCAN_INTERVAL_METADATA_MAX: Final[int] = 3600
OPTIONS_TIMEOUT_MIN: Final[float] = 2.0
OPTIONS_TIMEOUT_MAX: Final[float] = 30.0
OPTIONS_RETRY_ATTEMPTS_MIN: Final[int] = 1
OPTIONS_RETRY_ATTEMPTS_MAX: Final[int] = 10
OPTIONS_BACKOFF_INITIAL_MIN: Final[float] = 0.0
OPTIONS_BACKOFF_INITIAL_MAX: Final[float] = 5.0
OPTIONS_BACKOFF_MAX_MIN: Final[float] = 0.5
OPTIONS_BACKOFF_MAX_MAX: Final[float] = 30.0
OPTIONS_DTU_UNREACHABLE_MIN_MIN: Final[int] = 1
OPTIONS_DTU_UNREACHABLE_MIN_MAX: Final[int] = 60
OPTIONS_INVERTER_OFFLINE_H_MIN: Final[int] = 1
OPTIONS_INVERTER_OFFLINE_H_MAX: Final[int] = 168

# ─── Environmental impact factor defaults & range bounds (PR #6c) ──────────────
DEFAULT_CO2_FACTOR_KG_PER_KWH: Final[float] = 0.5
"""Default CO2 emission factor (kg CO2 avoided per kWh produced).

This default reflects a balanced European-average grid carbon intensity:
neither the very low value of France's nuclear-dominated grid nor the
worst-case coal-only marketing baseline used by some manufacturer apps.

Configurable via the OptionsFlow if you want a different reference:
  * France (RTE 2024):           0.053 kg/kWh — very low carbon (nuclear).
  * EU 27 mix (EEA 2024):        0.30 kg/kWh.
  * Germany (Umweltbundesamt):   0.50 kg/kWh — large coal share.
  * Hoymiles app default:        1.0 kg/kWh — coal-grid marketing baseline.
  * Coal-dominant regions:       1.0+ kg/kWh.

Cross-source note: the official Hoymiles mobile app uses 1.0 kg/kWh, so
its "CO2 reduced" display will read about twice the value of this
integration with the default 0.5. Users who prefer cross-source parity
can raise the factor to 1.0 via the OptionsFlow.
"""

DEFAULT_TREE_KG_CO2_PER_YEAR: Final[float] = 25.0
"""Default CO2 absorbed per planted tree per year (kg).

Standard ADEME (Agence de la transition écologique, France) reference value
for a mature European tree, also used widely in scientific-popularisation
materials. The value covers leaves + trunk + root growth over a year.

Lower the value for younger / slower-growing climates, raise it for tropical
species via the OptionsFlow:
  * Hoymiles app default:    18 kg/tree/year — young planted tree, growth phase.
  * EcoTree / OneTreePlanted: 20 kg/tree/year — average growth tree.
  * ADEME mature tree:       25 kg/tree/year — this default.
  * Tropical mature tree:    50 kg/tree/year — Trees For The Future estimate.
"""

OPTIONS_CO2_FACTOR_MIN: Final[float] = 0.0
"""Lower bound for CO2 factor: 0 disables the sensor (always 0)."""
OPTIONS_CO2_FACTOR_MAX: Final[float] = 2.0
"""Upper bound: 2.0 covers the worst coal-grid + lifecycle worst case."""

OPTIONS_TREE_KG_PER_YEAR_MIN: Final[float] = 5.0
"""Lower bound: very young saplings."""
OPTIONS_TREE_KG_PER_YEAR_MAX: Final[float] = 50.0
"""Upper bound: large mature tropical trees (rainforest)."""

# ─── Repair Issue thresholds (PR #2 hardcoded → PR #4 user-configurable) ──────
ISSUE_DTU_UNREACHABLE_THRESHOLD: Final[timedelta] = timedelta(minutes=5)
"""Default threshold before raising `dtu_unreachable`. Overridable via
`CONF_DTU_UNREACHABLE_THRESHOLD_MIN` in entry.options (PR #4)."""

ISSUE_INVERTER_OFFLINE_THRESHOLD: Final[timedelta] = timedelta(hours=6)
"""Default threshold before raising `inverter_offline_long`. Only counts AFTER
the inverter has been seen online at least once since the integration started.
Overridable via `CONF_INVERTER_OFFLINE_THRESHOLD_H` in entry.options (PR #4)."""

ISSUE_ID_DTU_UNREACHABLE: Final[str] = "dtu_unreachable"
"""Repair issue ID prefix; final ID is `f"{prefix}_{entry.entry_id}"`."""

ISSUE_ID_INVERTER_OFFLINE: Final[str] = "inverter_offline"
"""Repair issue ID prefix; final ID is `f"{prefix}_{serial}_{entry.entry_id}"`."""

# ─── Logger names declared in manifest.json ───────────────────────────────────
LOGGER_NAME: Final[str] = f"custom_components.{DOMAIN}"

__all__ = [
    "CONF_BACKOFF_INITIAL_S",
    "CONF_BACKOFF_MAX_S",
    "CONF_CO2_FACTOR_KG_PER_KWH",
    "CONF_DTU_UNREACHABLE_THRESHOLD_MIN",
    "CONF_HOST",
    "CONF_INVERTER_OFFLINE_THRESHOLD_H",
    "CONF_PORT",
    "CONF_RETRY_ATTEMPTS",
    "CONF_SCAN_INTERVAL_METADATA",
    "CONF_SCAN_INTERVAL_REAL_DATA",
    "CONF_TIMEOUT_S",
    "CONF_TREE_KG_CO2_PER_YEAR",
    "CONF_UNIT_ID",
    "DEFAULT_BACKOFF_INITIAL_S",
    "DEFAULT_BACKOFF_MAX_S",
    "DEFAULT_CO2_FACTOR_KG_PER_KWH",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_SCAN_INTERVAL_METADATA",
    "DEFAULT_SCAN_INTERVAL_REAL_DATA",
    "DEFAULT_TIMEOUT_S",
    "DEFAULT_TREE_KG_CO2_PER_YEAR",
    "DOMAIN",
    "ISSUE_DTU_UNREACHABLE_THRESHOLD",
    "ISSUE_ID_DTU_UNREACHABLE",
    "ISSUE_ID_INVERTER_OFFLINE",
    "ISSUE_INVERTER_OFFLINE_THRESHOLD",
    "LOGGER_NAME",
    "MIN_SCAN_INTERVAL_SECONDS",
    "OPTIONS_BACKOFF_INITIAL_MAX",
    "OPTIONS_BACKOFF_INITIAL_MIN",
    "OPTIONS_BACKOFF_MAX_MAX",
    "OPTIONS_BACKOFF_MAX_MIN",
    "OPTIONS_CO2_FACTOR_MAX",
    "OPTIONS_CO2_FACTOR_MIN",
    "OPTIONS_DTU_UNREACHABLE_MIN_MAX",
    "OPTIONS_DTU_UNREACHABLE_MIN_MIN",
    "OPTIONS_INVERTER_OFFLINE_H_MAX",
    "OPTIONS_INVERTER_OFFLINE_H_MIN",
    "OPTIONS_RETRY_ATTEMPTS_MAX",
    "OPTIONS_RETRY_ATTEMPTS_MIN",
    "OPTIONS_SCAN_INTERVAL_METADATA_MAX",
    "OPTIONS_SCAN_INTERVAL_METADATA_MIN",
    "OPTIONS_SCAN_INTERVAL_REAL_DATA_MAX",
    "OPTIONS_SCAN_INTERVAL_REAL_DATA_MIN",
    "OPTIONS_TIMEOUT_MAX",
    "OPTIONS_TIMEOUT_MIN",
    "OPTIONS_TREE_KG_PER_YEAR_MAX",
    "OPTIONS_TREE_KG_PER_YEAR_MIN",
]
