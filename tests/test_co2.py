"""Pure-unit tests for the CO2 / equivalent-trees derivation logic (PR #6c + #6d).

These tests exercise `HoymilesEnvironmentalSensor.native_value` directly via a
synthetic coordinator -- no Home Assistant runtime, no PHCC. They cover:

  * Today variants (PR #6c) — derived from `coordinator.plant_today_production_clamped`.
    Default-factor calculations against the canonical fixture
    (`mock_plant_data`: 7 inverters * 2 ports * 1850 Wh today = 25 900 Wh plant).
  * Lifetime variants (PR #6d) — derived from `coordinator.data.total_production`.
    Default-factor calculations against the canonical fixture
    (7 inverters * 985 000 Wh, dedup'd by serial = 6 895 000 Wh = 6895 kWh plant).
  * Override factors via `coordinator.config_entry.options`.
  * Defensive paths: zero factor, missing data, pre-first-poll None.

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
    # PR #7: the environmental sensor reads the RF-flap-clamped value via the
    # coordinator's `plant_today_production_clamped` property, not directly off
    # `data.today_production`. Mirror the raw plant sum here so the existing
    # arithmetic-based tests keep their reference values.
    coord.plant_today_production_clamped = coord_data.today_production
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


def test_native_value_returns_none_before_first_poll(
    mock_plant_data: PlantData,
) -> None:
    """Before the first successful poll the clamped property is None — sensor unavailable."""
    coord = MagicMock()
    coord.data = mock_plant_data
    coord.plant_today_production_clamped = None
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


# ─── PR #7 — Environmental sensors must use the clamped value, not data.today_production ───


def test_co2_uses_clamped_value_not_raw_plant_data(mock_plant_data: PlantData) -> None:
    """CO2 must derive from the clamped property even when raw plant sum has dropped.

    Without this routing, an RF-flap-induced drop in `data.today_production` would
    surface in the CO2 sensor as a TOTAL_INCREASING drop — exactly the bug PR #7
    fixes for `today_production` itself.
    """
    coord = MagicMock()
    coord.data = mock_plant_data  # raw = 25.9 kWh
    # Simulate a post-flap snapshot: raw is low, cache holds the pre-flap value.
    coord.plant_today_production_clamped = mock_plant_data.today_production
    coord.config_entry = MagicMock()
    coord.config_entry.options = {}

    description = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == "co2_savings_today")
    sensor = HoymilesEnvironmentalSensor.__new__(HoymilesEnvironmentalSensor)
    sensor.coordinator = coord
    sensor.entity_description = description

    # Now force the raw plant sum to a drastically lower value AFTER the sensor
    # is wired — the cached property is the only source of truth.
    class _PostFlapPlant:
        today_production = 5_000  # raw dropped to 5 kWh (e.g. half inverters offline)

    coord.data = _PostFlapPlant()

    # Sensor still reports the pre-flap CO2 (12.95 kg), NOT a value derived from 5 kWh.
    assert sensor.native_value == pytest.approx(12.95)


def test_trees_uses_clamped_value_not_raw_plant_data(mock_plant_data: PlantData) -> None:
    """Same routing check as above, applied to the trees-equivalent sensor."""
    coord = MagicMock()
    coord.data = mock_plant_data
    coord.plant_today_production_clamped = mock_plant_data.today_production
    coord.config_entry = MagicMock()
    coord.config_entry.options = {}

    description = next(
        d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == "equivalent_trees_planted_today"
    )
    sensor = HoymilesEnvironmentalSensor.__new__(HoymilesEnvironmentalSensor)
    sensor.coordinator = coord
    sensor.entity_description = description

    class _PostFlapPlant:
        today_production = 5_000

    coord.data = _PostFlapPlant()

    # 25.9 kWh * 0.5 = 12.95 kg ; 12.95 / 25 = 0.518 -> 0.52 trees (pre-flap).
    assert sensor.native_value == pytest.approx(0.52)


# ─── PR #6d — Lifetime variants (derived from data.total_production) ─────────


def _build_lifetime_sensor(
    coord_data: PlantData,
    options: dict[str, float],
    description_key: str,
) -> HoymilesEnvironmentalSensor:
    """Wire a lifetime HoymilesEnvironmentalSensor — reads data.total_production.

    Unlike `_build_sensor` (today variants), lifetime sensors do NOT consult
    `plant_today_production_clamped`. They read `coordinator.data.total_production`
    directly. We still set the clamped property to a sentinel so any accidental
    read by the lifetime path would produce a glaringly wrong value.
    """
    coord = MagicMock()
    coord.data = coord_data
    coord.plant_today_production_clamped = -123_456  # sentinel — must NOT be read
    coord.config_entry = MagicMock()
    coord.config_entry.options = options

    description = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == description_key)
    sensor = HoymilesEnvironmentalSensor.__new__(HoymilesEnvironmentalSensor)
    sensor.coordinator = coord
    sensor.entity_description = description
    return sensor


def test_co2_savings_lifetime_with_default_factor(mock_plant_data: PlantData) -> None:
    """Plant lifetime = 7 * 985 kWh = 6895 kWh * 0.5 = 3447.5 kg CO2.

    Note: dedup by serial means 7 inverters contribute one reading each, not 14.
    """
    sensor = _build_lifetime_sensor(
        mock_plant_data, options={}, description_key="co2_savings_lifetime"
    )
    # 7 inverters * 985 000 Wh = 6 895 000 Wh = 6895 kWh * 0.5 = 3447.5 kg
    assert sensor.native_value == pytest.approx(3447.5)


def test_co2_savings_lifetime_with_french_grid_factor(mock_plant_data: PlantData) -> None:
    """Override factor -> 6895 kWh * 0.053 = ~365.44 kg (RTE 2024)."""
    sensor = _build_lifetime_sensor(
        mock_plant_data,
        options={CONF_CO2_FACTOR_KG_PER_KWH: 0.053},
        description_key="co2_savings_lifetime",
    )
    # 6895 * 0.053 = 365.435 -> rounded to 2 decimals = 365.44 (HA rounds half-to-even).
    assert sensor.native_value == pytest.approx(365.44, abs=0.01)


def test_co2_savings_lifetime_with_zero_factor_returns_zero(
    mock_plant_data: PlantData,
) -> None:
    """Zero factor disables the lifetime CO2 sensor (always 0)."""
    sensor = _build_lifetime_sensor(
        mock_plant_data,
        options={CONF_CO2_FACTOR_KG_PER_KWH: 0.0},
        description_key="co2_savings_lifetime",
    )
    assert sensor.native_value == 0.0


def test_equivalent_trees_planted_lifetime_with_default_factors(
    mock_plant_data: PlantData,
) -> None:
    """3447.5 kg CO2 / 25 kg/tree/year = ~137.9 trees (defaults: 0.5 / 25)."""
    sensor = _build_lifetime_sensor(
        mock_plant_data, options={}, description_key="equivalent_trees_planted_lifetime"
    )
    # 6895 kWh * 0.5 = 3447.5 kg ; 3447.5 / 25 = 137.9
    assert sensor.native_value == pytest.approx(137.9)


def test_equivalent_trees_planted_lifetime_zero_tree_factor_returns_none(
    mock_plant_data: PlantData,
) -> None:
    """A non-positive tree factor cannot yield a meaningful trees count."""
    sensor = _build_lifetime_sensor(
        mock_plant_data,
        options={CONF_TREE_KG_CO2_PER_YEAR: 0.0},
        description_key="equivalent_trees_planted_lifetime",
    )
    assert sensor.native_value is None


def test_lifetime_sensors_return_none_when_coordinator_data_is_none() -> None:
    """Before the first successful poll, `coordinator.data` is None — sensor unavailable."""
    coord = MagicMock()
    coord.data = None
    coord.plant_today_production_clamped = None
    coord.config_entry = MagicMock()
    coord.config_entry.options = {}

    for key in ("co2_savings_lifetime", "equivalent_trees_planted_lifetime"):
        description = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == key)
        sensor = HoymilesEnvironmentalSensor.__new__(HoymilesEnvironmentalSensor)
        sensor.coordinator = coord
        sensor.entity_description = description
        assert sensor.native_value is None, f"{key} should be None when data is None"


def test_lifetime_sensors_do_not_consult_today_clamp(mock_plant_data: PlantData) -> None:
    """Lifetime variants must read `data.total_production`, NOT the today clamp.

    Regression guard: if a future refactor accidentally routes lifetime through
    `plant_today_production_clamped`, the sentinel value (-123 456) would surface
    as a nonsensical CO2 / trees value and this test would fail.
    """
    sensor = _build_lifetime_sensor(
        mock_plant_data, options={}, description_key="co2_savings_lifetime"
    )
    # Even though `plant_today_production_clamped` is -123_456 on the mock,
    # the lifetime sensor reads `data.total_production` = 6 895 000 Wh and
    # produces a sane positive value.
    assert sensor.native_value == pytest.approx(3447.5)


# ─── Descriptor-level assertions (lock down attributes) ───────────────────────


def test_today_environmental_descriptors_use_total_increasing() -> None:
    """Today variants: TOTAL_INCREASING (reset at midnight via HA meter logic)."""
    from homeassistant.components.sensor import SensorStateClass

    for key in ("co2_savings_today", "equivalent_trees_planted_today"):
        desc = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == key)
        assert desc.state_class == SensorStateClass.TOTAL_INCREASING


def test_lifetime_environmental_descriptors_use_total() -> None:
    """Lifetime variants: TOTAL (NOT TOTAL_INCREASING — DTU resets total_wh at midnight)."""
    from homeassistant.components.sensor import SensorStateClass

    for key in ("co2_savings_lifetime", "equivalent_trees_planted_lifetime"):
        desc = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == key)
        assert desc.state_class == SensorStateClass.TOTAL


def test_environmental_descriptors_are_not_diagnostic() -> None:
    """CO2/trees are user-facing, NOT DIAGNOSTIC (they go on the main device card)."""
    for desc in PLANT_ENVIRONMENTAL_SENSORS:
        assert desc.entity_category is None


def test_co2_descriptor_uses_kilograms() -> None:
    """CO2 mass uses HA's UnitOfMass.KILOGRAMS, not a raw 'kg' string.

    Both today and lifetime variants share the same unit/device-class shape.
    """
    from homeassistant.components.sensor import SensorDeviceClass
    from homeassistant.const import UnitOfMass

    for key in ("co2_savings_today", "co2_savings_lifetime"):
        desc = next(d for d in PLANT_ENVIRONMENTAL_SENSORS if d.key == key)
        assert desc.native_unit_of_measurement == UnitOfMass.KILOGRAMS, f"{key} unit"
        assert desc.device_class == SensorDeviceClass.WEIGHT, f"{key} device_class"
