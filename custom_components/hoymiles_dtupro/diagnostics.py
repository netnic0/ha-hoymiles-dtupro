"""Diagnostics platform — exposes anonymised state for issue triage (D11).

Users can download a JSON snapshot from Settings → Devices & Services → ⋮ → Download diagnostics.
The serial numbers are redacted to avoid leaking installation IDs in public bug reports.
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


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics data for a config entry."""
    bundle = hass.data[DOMAIN][entry.entry_id]
    real_coord = bundle["real_data"]
    metadata_coord = bundle["metadata"]

    payload = {
        "config_entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "version": entry.version,
        },
        "real_data": _plant_to_dict(real_coord.data) if real_coord.data else None,
        "metadata": _plant_to_dict(metadata_coord.data) if metadata_coord.data else None,
    }
    return async_redact_data(payload, REDACT_KEYS)
