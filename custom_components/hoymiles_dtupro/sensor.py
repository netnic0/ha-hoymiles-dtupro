"""Sensor platform — skeleton with 4 demonstrative entities.

Full sensor wiring for the 158 expected entities is part of M2; this module
demonstrates the modern pattern (translation_key + EntityDescription) for the
PoC review.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ha_hoymiles_dtupro import PlantData

from .const import DOMAIN
from .entity import HoymilesInverterEntity, HoymilesPlantEntity

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


# Defer HA imports for PoC offline path.
try:  # pragma: no cover
    from homeassistant.components.sensor import (
        SensorDeviceClass,
        SensorEntity,
        SensorEntityDescription,
        SensorStateClass,
    )
    from homeassistant.const import (
        UnitOfElectricPotential,
        UnitOfEnergy,
        UnitOfPower,
        UnitOfTemperature,
    )

    _HAS_HA = True
except ImportError:  # pragma: no cover
    _HAS_HA = False
    SensorEntity = object  # type: ignore[assignment,misc]
    SensorEntityDescription = dict  # type: ignore[assignment,misc]


if _HAS_HA:  # pragma: no cover
    PLANT_SENSORS: tuple[SensorEntityDescription, ...] = (
        SensorEntityDescription(
            key="pv_power",
            translation_key="pv_power",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
        ),
        SensorEntityDescription(
            key="today_production",
            translation_key="today_production",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        ),
        SensorEntityDescription(
            key="total_production",
            translation_key="total_production",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        ),
    )

    INVERTER_SENSORS: tuple[SensorEntityDescription, ...] = (
        SensorEntityDescription(
            key="temperature",
            translation_key="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        ),
        SensorEntityDescription(
            key="grid_voltage",
            translation_key="grid_voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        ),
    )


    class HoymilesPlantSensor(HoymilesPlantEntity, SensorEntity):  # type: ignore[misc]
        """A plant-level numeric sensor (pv_power, today_production, ...)."""

        entity_description: SensorEntityDescription

        def __init__(self, coordinator, description: SensorEntityDescription) -> None:
            super().__init__(coordinator, translation_key=description.translation_key or description.key)
            self.entity_description = description

        @property
        def native_value(self) -> float | int | None:
            data: PlantData = self.coordinator.data
            return getattr(data, self.entity_description.key, None)


    class HoymilesInverterSensor(HoymilesInverterEntity, SensorEntity):  # type: ignore[misc]
        """A per-inverter numeric sensor."""

        entity_description: SensorEntityDescription

        def __init__(self, coordinator, inverter_serial: str, description: SensorEntityDescription) -> None:
            super().__init__(
                coordinator,
                inverter_serial,
                translation_key=description.translation_key or description.key,
            )
            self.entity_description = description

        @property
        def native_value(self) -> float | int | None:
            data: PlantData = self.coordinator.data
            for inv in data.inverters:
                if inv.serial_number == self._inverter_serial:
                    return getattr(inv, self.entity_description.key, None)
            return None


    async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Wire the demonstrative sensors. Full set will follow in M2."""
        bundle = hass.data[DOMAIN][entry.entry_id]
        real_coord = bundle["real_data"]
        plant: PlantData = real_coord.data

        entities: list[SensorEntity] = []
        entities.extend(
            HoymilesPlantSensor(real_coord, desc) for desc in PLANT_SENSORS
        )
        for inverter in plant.inverters:
            entities.extend(
                HoymilesInverterSensor(real_coord, inverter.serial_number, desc)
                for desc in INVERTER_SENSORS
            )

        async_add_entities(entities)
