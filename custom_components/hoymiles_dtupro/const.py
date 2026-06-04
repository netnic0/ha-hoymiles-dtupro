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
DEFAULT_SCAN_INTERVAL_REAL_DATA: Final[timedelta] = timedelta(seconds=30)
"""Live data: pv_power, voltages, temperature."""

DEFAULT_SCAN_INTERVAL_METADATA: Final[timedelta] = timedelta(minutes=5)
"""Metadata: link_status, alarm_count, operating_status (rarely changes)."""

MIN_SCAN_INTERVAL_SECONDS: Final[int] = 10
"""Lower bound enforced by the config flow to avoid hammering the DTU."""

# ─── Logger names declared in manifest.json ───────────────────────────────────
LOGGER_NAME: Final[str] = f"custom_components.{DOMAIN}"
