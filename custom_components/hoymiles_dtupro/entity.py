"""Base entity classes for the Hoymiles DTU-Pro integration.

Two abstractions:
  * `HoymilesPlantEntity` — bound to the DTU device (parent).
  * `HoymilesInverterEntity` — bound to a specific inverter (child of the DTU
    via `via_device`, see D9 in REFERENCES_HACS_MODERNES_2026.md §6).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PlantData
from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import (
        HoymilesMetadataCoordinator,
        HoymilesRealDataCoordinator,
    )


class HoymilesPlantEntity(CoordinatorEntity[PlantData]):  # type: ignore[misc]
    """An entity attached to the DTU device itself (whole plant aggregates)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoymilesRealDataCoordinator | HoymilesMetadataCoordinator,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._dtu_serial = coordinator.data.dtu_serial
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{self._dtu_serial}_{translation_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._dtu_serial)},
            name=f"Hoymiles DTU-Pro ({self._dtu_serial})",
            manufacturer="Hoymiles",
            model="DTU-Pro",
        )


class HoymilesInverterEntity(CoordinatorEntity[PlantData]):  # type: ignore[misc]
    """An entity attached to a single inverter, parented to the DTU."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoymilesRealDataCoordinator | HoymilesMetadataCoordinator,
        inverter_serial: str,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._dtu_serial = coordinator.data.dtu_serial
        self._inverter_serial = inverter_serial
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{inverter_serial}_{translation_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, inverter_serial)},
            name=f"Hoymiles Inverter ({inverter_serial})",
            manufacturer="Hoymiles",
            model="HMS-1000-2T",  # default; could be derived from series prefix
            via_device=(DOMAIN, self._dtu_serial),
        )
