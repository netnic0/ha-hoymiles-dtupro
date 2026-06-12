"""Pure-unit tests for the CO2 / equivalent-trees derivation logic (PR #6c).

These tests exercise `HoymilesEnvironmentalSensor.native_value` directly via a
synthetic coordinator -- no Home Assistant runtime, no PHCC. They cover:

  * Default-factor calculations against the canonical fixture
    (`mock_plant_data`: 7 inverters * 2 ports * 1850 Wh today = 25 900 Wh plant).
  * Override factors via `coordinator.config_entry.options`.
  * Defensive paths: zero, negative, missing data.

The HA-native side (entity registration, options-flow propagation) lives in
`tests/test_sensor.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.hoymiles_dtupro.const import (
    CONF_CO2_FACTOR_KG_PER_KWH,
    CONF_TREE_KG_CO2_PER_YEAR,
    DEFAULT_CO2_FACTOR_KG_PER_KWH,
    DEFAULT_TREE_KG_CO2_PER_YEAR,
)
from custom_components.hoymiles_dtupro.sensor import (
    PLANT_ENVIRONMENTAL_SENSORS,
    HoymilesEnvironmentalSensor,
)

if TYPE_CHECKING:
    from custom_components.hoymiles_dtupro.api.models import PlantData


def _build_sensor(
    coord_data: PlantData,
    options: dict[str, float],
    description_key: str,
) -> HoymilesEnvironmentalSensor:
    """Wire a HoymilesEnvironmentalSensor without going through HA's setup."""
    coord = MagicMock()
    coord.data = coord_data
    coord.config_entry = MagicMock()
    coord.config_entry.options = options

    description = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == description_key)
    sensor = HoymilesEnvironmentalSensor.__new__(HoymilesEnvironmentalSensor)
    sensor.coordinator = coord
    sensor.entity_description = description
    return sensor


# ─── CO2 savings ──────────────────────────────────────────────────────────────


def test_co2_savings_today_with_default_factor(mock_plant_data: PlantData) -> None:
    """Plant today = 25.9 kWh * default factor 0.5 = 12.95 kg CO2."""
    sensor = _build_sensor(mock_plant_data, options={}, description_key="co2_savings_today")
    # 14 readings * 1850 Wh = 25 900 Wh = 25.9 kWh * 0.5 = 12.95 kg
    assert sensor.native_value == pytest.approx(12.95)


def test_co2_savings_today_with_french_grid_factor(mock_plant_data: PlantData) -> None:
    """Override factor -> 25.9 kWh * 0.053 = ~1.37 kg (RTE 2024)."""
    sensor = _build_sensor(
        mock_plant_data,
        options={CONF_CO2_FACTOR_KG_PER_KWH: 0.053},
        description_key="co2_savings_today",
    )
    # 25.9 * 0.053 = 1.3727 -> rounded to 2 decimals = 1.37
    assert sensor.native_value == pytest.approx(1.37)


def test_co2_savings_today_with_zero_factor_returns_zero(mock_plant_data: PlantData) -> None:
    """Zero factor disables the sensor (always 0)."""
    sensor = _build_sensor(
        mock_plant_data,
        options={CONF_CO2_FACTOR_KG_PER_KWH: 0.0},
        description_key="co2_savings_today",
    )
    assert sensor.native_value == 0.0


# --- Equivalent trees planted ------------------------------------------------


def test_equivalent_trees_planted_today_with_default_factors(mock_plant_data: PlantData) -> None:
    """12.95 kg CO2 / 25 kg/tree/year = ~0.52 trees (defaults: 0.5 / 25)."""
    sensor = _build_sensor(
        mock_plant_data, options={}, description_key="equivalent_trees_planted_today"
    )
    # 25.9 kWh * 0.5 = 12.95 kg ; 12.95 / 25 = 0.518 -> 2 decimals = 0.52
    assert sensor.native_value == pytest.approx(0.52)


def test_equivalent_trees_planted_today_with_overridden_factors(
    mock_plant_data: PlantData,
) -> None:
    """Override both factors and verify the formula chains correctly (Hoymiles-style)."""
    sensor = _build_sensor(
        mock_plant_data,
        options={
            CONF_CO2_FACTOR_KG_PER_KWH: 1.0,
            CONF_TREE_KG_CO2_PER_YEAR: 18.0,
        },
        description_key="equivalent_trees_planted_today",
    )
    # 25.9 kWh * 1.0 = 25.9 kg CO2 ; 25.9 / 18 = 1.4388... -> 2 decimals = 1.44
    assert sensor.native_value == pytest.approx(1.44)


def test_equivalent_trees_planted_today_zero_tree_factor_returns_none(
    mock_plant_data: PlantData,
) -> None:
    """A non-positive tree factor cannot yield a meaningful trees count."""
    sensor = _build_sensor(
        mock_plant_data,
        options={CONF_TREE_KG_CO2_PER_YEAR: 0.0},
        description_key="equivalent_trees_planted_today",
    )
    assert sensor.native_value is None


# ─── Defensive: invalid / missing inputs ──────────────────────────────────────


def test_native_value_returns_none_when_today_production_is_negative(
    mock_plant_data: PlantData,
) -> None:
    """Defensive: a negative today_production (impossible, but defensive)."""
    coord = MagicMock()

    # Patch the data so today_production becomes a negative int via a stub.
    class _BadPlant:
        today_production = -1

    coord.data = _BadPlant()
    coord.config_entry = MagicMock()
    coord.config_entry.options = {}

    description = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == "co2_savings_today")
    sensor = HoymilesEnvironmentalSensor.__new__(HoymilesEnvironmentalSensor)
    sensor.coordinator = coord
    sensor.entity_description = description

    assert sensor.native_value is None


def test_factors_helper_returns_defaults_when_options_empty(mock_plant_data: PlantData) -> None:
    """`_factors()` falls back to integration defaults when entry.options is empty."""
    sensor = _build_sensor(mock_plant_data, options={}, description_key="co2_savings_today")
    co2, tree = sensor._factors()
    assert co2 == DEFAULT_CO2_FACTOR_KG_PER_KWH
    assert tree == DEFAULT_TREE_KG_CO2_PER_YEAR


# ─── Descriptor-level assertions (lock down attributes) ───────────────────────


def test_environmental_descriptors_are_plant_only() -> None:
    """Both environmental sensors are TOTAL_INCREASING (reset at midnight)."""
    from homeassistant.components.sensor import SensorStateClass

    for desc in PLANT_ENVIRONMENTAL_SENSORS:
        assert desc.state_class == SensorStateClass.TOTAL_INCREASING


def test_environmental_descriptors_are_not_diagnostic() -> None:
    """CO2/trees are user-facing, NOT DIAGNOSTIC (they go on the main device card)."""
    for desc in PLANT_ENVIRONMENTAL_SENSORS:
        assert desc.entity_category is None


def test_co2_descriptor_uses_kilograms() -> None:
    """CO2 mass uses HA's UnitOfMass.KILOGRAMS, not a raw 'kg' string."""
    from homeassistant.components.sensor import SensorDeviceClass
    from homeassistant.const import UnitOfMass

    desc = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == "co2_savings_today")
    assert desc.native_unit_of_measurement == UnitOfMass.KILOGRAMS
    assert desc.device_class == SensorDeviceClass.WEIGHT
