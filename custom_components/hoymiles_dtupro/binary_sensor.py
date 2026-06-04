"""Binary sensor platform — `link_status` per inverter + global `alarm` flag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ha_hoymiles_dtupro import PlantData

from .const import DOMAIN
from .entity import HoymilesInverterEntity, HoymilesPlantEntity

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


try:  # pragma: no cover
    from homeassistant.components.binary_sensor import (
        BinarySensorDeviceClass,
        BinarySensorEntity,
        BinarySensorEntityDescription,
    )

    _HAS_HA = True
except ImportError:  # pragma: no cover
    _HAS_HA = False
    BinarySensorEntity = object  # type: ignore[assignment,misc]


if _HAS_HA:  # pragma: no cover
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

    class HoymilesAlarmBinarySensor(HoymilesPlantEntity, BinarySensorEntity):  # type: ignore[misc]
        """True iff any online inverter is reporting an alarm."""

        def __init__(self, coordinator) -> None:
            super().__init__(coordinator, translation_key="alarm")
            self.entity_description = ALARM_DESC

        @property
        def is_on(self) -> bool:
            data: PlantData = self.coordinator.data
            return data.alarm_flag

    class HoymilesLinkBinarySensor(HoymilesInverterEntity, BinarySensorEntity):  # type: ignore[misc]
        """Per-inverter RF link reachability."""

        def __init__(self, coordinator, inverter_serial: str) -> None:
            super().__init__(coordinator, inverter_serial, translation_key="link")
            self.entity_description = LINK_DESC

        @property
        def is_on(self) -> bool:
            data: PlantData = self.coordinator.data
            for inv in data.inverters:
                if inv.serial_number == self._inverter_serial:
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
        entities.extend(
            HoymilesLinkBinarySensor(real_coord, inv.serial_number) for inv in plant.inverters
        )
        async_add_entities(entities)
