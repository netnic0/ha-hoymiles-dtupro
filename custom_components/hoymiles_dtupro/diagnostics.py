"""Diagnostics platform — exposes anonymised state for issue triage (D11).

Users can download a JSON snapshot from Settings → Devices & Services → ⋮ → Download diagnostics.
The serial numbers are redacted to avoid leaking installation IDs in public bug reports.

Sections:
  * ``config_entry``      — generic title + non-PII config entry data.
  * ``real_data`` / ``metadata`` — current PlantData snapshots from each coordinator.
  * ``coordinator_state`` — runtime health: last update success/timestamps,
    effective polling intervals, online inverter count.

No raw Modbus frames or per-inverter timestamps are exposed (PR #2 scope —
deliberately conservative on what gets dumped to a public issue tracker).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data

from .api import PlantData
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


REDACT_KEYS: set[str] = {"host", "serial_number", "dtu_serial"}


def _plant_to_dict(plant: PlantData) -> dict[str, Any]:
    return {
        "dtu_serial": plant.dtu_serial,
        "fetched_at": plant.fetched_at.isoformat(),
        "inverter_count": plant.inverter_count,
        "online_inverter_count": len(plant.online_inverters),
        "pv_power": plant.pv_power,
        "today_production": plant.today_production,
        "total_production": plant.total_production,
        "alarm_flag": plant.alarm_flag,
        "inverters": [
            {
                "serial_number": inv.serial_number,
                "port_number": inv.port_number,
                "pv_power": inv.pv_power,
                "temperature": inv.temperature,
                "link_status": inv.link_status,
                "alarm_code": inv.alarm_code,
                "alarm_count": inv.alarm_count,
            }
            for inv in plant.inverters
        ],
    }


def _coordinator_state(real_coord: Any, metadata_coord: Any) -> dict[str, Any]:
    """Per-coordinator runtime health snapshot.

    Reports the *runtime* values (e.g. ``coordinator.update_interval``) rather
    than the values stored in ``entry.data``. They can diverge — see the
    pre-existing ``CONF_SCAN_INTERVAL_REAL_DATA`` saved-but-not-read issue
    that PR #4 (OptionsFlow) will address.
    """

    def _summarise(coord: Any) -> dict[str, Any]:
        last_ok = coord.last_update_success_time
        return {
            "last_update_success": coord.last_update_success,
            "last_update_success_time": last_ok.isoformat() if last_ok else None,
            "update_interval_seconds": (
                coord.update_interval.total_seconds() if coord.update_interval else None
            ),
            "online_inverter_count": (
                len(coord.data.online_inverters) if coord.data is not None else None
            ),
            "inverter_count": (coord.data.inverter_count if coord.data is not None else None),
        }

    return {
        "real_data": _summarise(real_coord),
        "metadata": _summarise(metadata_coord),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics data for a config entry."""
    bundle = hass.data[DOMAIN][entry.entry_id]
    real_coord = bundle["real_data"]
    metadata_coord = bundle["metadata"]

    # The entry title bakes the DTU serial ("Hoymiles DTU-Pro (<SN>)") for UX,
    # so emit a generic title in diagnostics rather than the live one — otherwise
    # the SN leaks despite REDACT_KEYS covering the structured fields.
    payload = {
        "config_entry": {
            "title": "Hoymiles DTU-Pro",
            "data": dict(entry.data),
            "version": entry.version,
        },
        "real_data": _plant_to_dict(real_coord.data) if real_coord.data else None,
        "metadata": _plant_to_dict(metadata_coord.data) if metadata_coord.data else None,
        "coordinator_state": _coordinator_state(real_coord, metadata_coord),
    }
    return async_redact_data(payload, REDACT_KEYS)
