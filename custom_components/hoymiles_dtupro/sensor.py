"""Sensor platform for the Hoymiles DTU-Pro integration.

Entities created:
  * Plant-level (attached to the DTU device):
      pv_power, today_production, total_production,
      co2_savings_today, equivalent_trees_planted_today (PR #6c)

  * Per-inverter (one set per detected inverter, port-agnostic):
      temperature, grid_voltage, grid_frequency, alarm_code, alarm_count

  * Per-port (one set per inverter x MPPT port -- HMS-1000-2T has 2):
      pv_voltage, pv_current, pv_power, today_production, total_production

Full entity count for 7 HMS-1000-2T inverters with 2 ports each:
  5 (plant) + 7*5 (inverter) + 7*2*5 (port) = 5 + 35 + 70 = 110 sensors.
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
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
)

from .api import PlantData
from .const import (
    CONF_CO2_FACTOR_KG_PER_KWH,
    CONF_TREE_KG_CO2_PER_YEAR,
    DEFAULT_CO2_FACTOR_KG_PER_KWH,
    DEFAULT_TREE_KG_CO2_PER_YEAR,
    DOMAIN,
)
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


# ─── Environmental impact sensors (PR #6c, plant-level only) ──────────────────
# Defaults reflect a balanced European-average grid carbon intensity (0.5 kg/kWh)
# and the ADEME standard for a mature European tree (25 kg CO2 absorbed/year).
# Both factors are user-configurable via the OptionsFlow — see strings.json
# `data_description` for reference values matching France/EU/Germany/Hoymiles.
PLANT_ENVIRONMENTAL_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="co2_savings_today",
        translation_key="co2_savings_today",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        icon="mdi:molecule-co2",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="equivalent_trees_planted_today",
        translation_key="equivalent_trees_planted_today",
        # No device_class: "trees" is not a HA standard quantity.
        # state_class TOTAL_INCREASING mirrors today_production (resets at midnight).
        state_class=SensorStateClass.TOTAL_INCREASING,
        # No native_unit_of_measurement: pure count, but a fractional float so the
        # value is always informative even on low-production days (winter ≈ 0.05).
        icon="mdi:tree-outline",
        suggested_display_precision=2,
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


class HoymilesPlantSensor(HoymilesPlantEntity, SensorEntity):
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
        # `today_production` MUST be read through the coordinator's RF-flap cache,
        # NOT from `data.today_production`. The raw plant sum drops every time an
        # inverter's RF link flaps, and HA's recorder reads each drop on a
        # state_class=TOTAL_INCREASING sensor as a counter reset — inflating the
        # Energy dashboard by 10-20x. See `TodayCache` in coordinator.py. All
        # other plant keys (pv_power, total_production) remain safe direct reads.
        if self.entity_description.key == "today_production":
            return self.coordinator.plant_today_production_clamped
        data: PlantData = self.coordinator.data
        return getattr(data, self.entity_description.key, None)


class HoymilesEnvironmentalSensor(HoymilesPlantEntity, SensorEntity):
    """A derived plant-level sensor for CO2 savings or equivalent trees planted.

    Distinct from `HoymilesPlantSensor` because the value is NOT a direct
    attribute of `PlantData` — it is computed from `data.today_production`
    (Wh) and one or two user-configurable factors stored in
    `entry.options`. PR #6c (Option B in the plan-reviewer audit) keeps the
    `api/` sub-package free of HA configuration knowledge: business logic
    lives in the HA layer.

    This class is forward-compatible with PR #6d (lifetime variants): a future
    subclass could swap `today_production` for a fixed `total_production`
    once Bug A is resolved.
    """

    entity_description: SensorEntityDescription

    def __init__(
        self, coordinator: HoymilesRealDataCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(
            coordinator, translation_key=description.translation_key or description.key
        )
        self.entity_description = description

    def _factors(self) -> tuple[float, float]:
        """Read the two factors from entry.options, falling back to defaults.

        Returns a tuple `(co2_factor_kg_per_kwh, tree_kg_co2_per_year)`.
        """
        # `config_entry` is provided by HA on the CoordinatorEntity since
        # 2024.4 (see homeassistant.helpers.update_coordinator). Fall back to
        # an empty dict if absent — defensive only, never reached in practice.
        options = getattr(self.coordinator.config_entry, "options", {}) or {}
        co2_factor = float(options.get(CONF_CO2_FACTOR_KG_PER_KWH, DEFAULT_CO2_FACTOR_KG_PER_KWH))
        tree_factor = float(options.get(CONF_TREE_KG_CO2_PER_YEAR, DEFAULT_TREE_KG_CO2_PER_YEAR))
        return co2_factor, tree_factor

    @property
    def native_value(self) -> float | None:
        """Compute the sensor value from `today_production` and the factors."""
        # Read the RF-flap-clamped plant value via the coordinator. Falling back
        # to `data.today_production` would re-introduce the drops the cache
        # exists to suppress (CO2 and trees-today are TOTAL_INCREASING and feed
        # the Energy dashboard's daily figures through utility_meter cycles).
        today_wh = self.coordinator.plant_today_production_clamped
        if today_wh is None or today_wh < 0:
            return None
        today_kwh = today_wh / 1000.0
        co2_factor, tree_factor = self._factors()

        if self.entity_description.key == "co2_savings_today":
            # kg CO2 saved = kWh * (kg CO2 / kWh)
            return round(today_kwh * co2_factor, 2)

        if self.entity_description.key == "equivalent_trees_planted_today":
            # arbres équivalents = (kg CO2 saved today) / (kg CO2 / arbre / an)
            # Note: the unit of the numerator (today, in kg) and the unit of the
            # denominator (per year) are intentionally NOT homogeneous — this
            # mirrors the Hoymiles app convention which gives a "fractional
            # tree per day" snapshot. Aggregating via utility_meter cycle:yearly
            # gives a meaningful "trees per year".
            if tree_factor <= 0:
                return None
            kg_today = today_kwh * co2_factor
            return round(kg_today / tree_factor, 2)

        return None  # pragma: no cover — descriptor not registered for this class


class HoymilesInverterSensor(HoymilesInverterEntity, SensorEntity):
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


class HoymilesInverterPortSensor(HoymilesInverterEntity, SensorEntity):
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
    entities.extend(
        HoymilesEnvironmentalSensor(real_coord, desc) for desc in PLANT_ENVIRONMENTAL_SENSORS
    )

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
