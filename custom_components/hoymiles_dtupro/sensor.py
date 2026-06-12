"""Sensor platform for the Hoymiles DTU-Pro integration.

Entities created:
  * Plant-level (attached to the DTU device):
      pv_power, today_production, total_production

  * Per-inverter (one set per detected inverter, port-agnostic):
      temperature, grid_voltage, grid_frequency, alarm_code, alarm_count

  * Per-port (one set per inverter x MPPT port -- HMS-1000-2T has 2):
      pv_voltage, pv_current, pv_power, today_production, total_production

Full entity count for 7 HMS-1000-2T inverters with 2 ports each:
  3 (plant) + 7*5 (inverter) + 7*2*5 (port) = 3 + 35 + 70 = 108 sensors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.entity import EntityCategory

from .api import PlantData
from .const import DOMAIN
from .entity import HoymilesInverterEntity, HoymilesPlantEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import HoymilesRealDataCoordinator


# Silver quality_scale: declare that this platform imposes no concurrency limit
# of its own. The DataUpdateCoordinator already serialises Modbus polling via
# its internal lock and the client mutex, so platform-level throttling would be
# redundant. 0 = "as many parallel updates as the entity registry chooses".
PARALLEL_UPDATES = 0


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
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="total_production",
        translation_key="total_production",
        # state_class TOTAL (not TOTAL_INCREASING): the DTU resets the lifetime
        # counter at midnight (see commit 13b3a13). TOTAL handles those resets
        # without HA recorder warnings while still feeding long-term statistics.
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
    SensorEntityDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    SensorEntityDescription(
        key="alarm_code",
        translation_key="alarm_code",
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="alarm_count",
        translation_key="alarm_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

PORT_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="pv_voltage",
        translation_key="pv_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SensorEntityDescription(
        key="pv_current",
        translation_key="pv_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
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
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="total_production",
        translation_key="total_production",
        # See PLANT_SENSORS comment: TOTAL (not TOTAL_INCREASING) due to DTU
        # midnight reset of the per-port lifetime counter (commit 13b3a13).
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
)


class HoymilesPlantSensor(HoymilesPlantEntity, SensorEntity):  # type: ignore[misc]
    """A plant-level numeric sensor aggregated across all online inverters."""

    entity_description: SensorEntityDescription

    def __init__(
        self, coordinator: HoymilesRealDataCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(
            coordinator, translation_key=description.translation_key or description.key
        )
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        data: PlantData = self.coordinator.data
        return getattr(data, self.entity_description.key, None)


class HoymilesInverterSensor(HoymilesInverterEntity, SensorEntity):  # type: ignore[misc]
    """A per-inverter sensor for port-agnostic fields (temperature, grid, alarms).

    Reads from port_number == 1 since those fields are identical across ports.
    """

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: HoymilesRealDataCoordinator,
        inverter_serial: str,
        description: SensorEntityDescription,
    ) -> None:
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
            if inv.serial_number == self._inverter_serial and inv.port_number == 1:
                return getattr(inv, self.entity_description.key, None)
        return None


class HoymilesInverterPortSensor(HoymilesInverterEntity, SensorEntity):  # type: ignore[misc]
    """A per-MPPT-port sensor for PV-side measurements.

    HMS-1000-2T has 2 MPPT inputs; unique_id includes the port number so HA
    registers them as distinct entities (e.g. 'PV power 1' vs 'PV power 2').
    """

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: HoymilesRealDataCoordinator,
        inverter_serial: str,
        port_number: int,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(
            coordinator,
            inverter_serial,
            translation_key=description.translation_key or description.key,
        )
        self._port_number = port_number
        self._attr_unique_id = f"{inverter_serial}_p{port_number}_{description.key}"
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        data: PlantData = self.coordinator.data
        for inv in data.inverters:
            if inv.serial_number == self._inverter_serial and inv.port_number == self._port_number:
                return getattr(inv, self.entity_description.key, None)
        return None

    @property
    def name(self) -> str | None:
        """Append port number to distinguish e.g. 'PV power 1' from 'PV power 2'."""
        base = super().name
        return f"{base} {self._port_number}" if base else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register all sensor entities for this config entry."""
    bundle = hass.data[DOMAIN][entry.entry_id]
    real_coord = bundle["real_data"]
    plant: PlantData = real_coord.data

    entities: list[SensorEntity] = []

    entities.extend(HoymilesPlantSensor(real_coord, desc) for desc in PLANT_SENSORS)

    seen_serials: set[str] = set()
    for inv in plant.inverters:
        serial = inv.serial_number
        if serial not in seen_serials:
            seen_serials.add(serial)
            entities.extend(
                HoymilesInverterSensor(real_coord, serial, desc) for desc in INVERTER_SENSORS
            )
        entities.extend(
            HoymilesInverterPortSensor(real_coord, serial, inv.port_number, desc)
            for desc in PORT_SENSORS
        )

    async_add_entities(entities)
