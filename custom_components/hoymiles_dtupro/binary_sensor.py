"""Binary sensor platform for the Hoymiles DTU-Pro integration.

Entities:
  * One plant-level alarm binary_sensor (DTU device).
  * One link binary_sensor per inverter (reads port_number == 1; link_status is
    identical across ports so only one entity per inverter is needed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .api import PlantData
from .const import DOMAIN
from .entity import HoymilesInverterEntity, HoymilesPlantEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


ALARM_DESC = BinarySensorEntityDescription(
    key="alarm",
    translation_key="alarm",
    device_class=BinarySensorDeviceClass.PROBLEM,
)

LINK_DESC = BinarySensorEntityDescription(
    key="link",
    translation_key="link",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


class HoymilesAlarmBinarySensor(HoymilesPlantEntity, BinarySensorEntity):
    """True iff any online inverter is reporting an alarm."""

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, translation_key="alarm")
        self.entity_description = ALARM_DESC

    @property
    def is_on(self) -> bool:
        data: PlantData = self.coordinator.data
        return data.alarm_flag


class HoymilesLinkBinarySensor(HoymilesInverterEntity, BinarySensorEntity):
    """Per-inverter RF link reachability."""

    def __init__(self, coordinator, inverter_serial: str) -> None:
        super().__init__(coordinator, inverter_serial, translation_key="link")
        self.entity_description = LINK_DESC

    @property
    def is_on(self) -> bool:
        data: PlantData = self.coordinator.data
        for inv in data.inverters:
            if inv.serial_number == self._inverter_serial and inv.port_number == 1:
                return inv.link_status
        return False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    bundle = hass.data[DOMAIN][entry.entry_id]
    real_coord = bundle["real_data"]
    plant: PlantData = real_coord.data

    entities: list[BinarySensorEntity] = [HoymilesAlarmBinarySensor(real_coord)]

    seen_serials: set[str] = set()
    for inv in plant.inverters:
        serial = inv.serial_number
        if serial not in seen_serials:
            seen_serials.add(serial)
            entities.append(HoymilesLinkBinarySensor(real_coord, serial))

    async_add_entities(entities)
