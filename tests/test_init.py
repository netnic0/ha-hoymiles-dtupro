"""HA-native tests for setup, unload, and reload of the Hoymiles DTU-Pro entry."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hoymiles_dtupro import async_migrate_entry
from custom_components.hoymiles_dtupro.const import (
    CONF_CO2_FACTOR_KG_PER_KWH,
    CONF_SCAN_INTERVAL_REAL_DATA,
    CONF_TREE_KG_CO2_PER_YEAR,
    DEFAULT_CO2_FACTOR_KG_PER_KWH,
    DEFAULT_TREE_KG_CO2_PER_YEAR,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.hoymiles_dtupro.api.models import PlantData


# Patch target for the API client used inside async_setup_entry.
# The lazy import pattern means HoymilesAsyncClient lives at module path .api,
# not at the integration package root.
_CLIENT_PATH = "custom_components.hoymiles_dtupro.api.HoymilesAsyncClient"


@pytest.mark.asyncio
async def test_async_setup_entry_creates_coordinators_and_loads_platforms(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """async_setup_entry stores client + two coordinators in hass.data and loads the platforms."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    bundle = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert bundle["client"] is fake_client
    assert bundle["real_data"].data is mock_plant_data
    assert bundle["metadata"].data is mock_plant_data

    # Both platforms (sensor + binary_sensor) should have at least one entity registered.
    entity_registry_ids = {
        e.entity_id
        for e in hass.states.async_all()
        if e.entity_id.startswith(("sensor.", "binary_sensor."))
    }
    assert any(eid.startswith("sensor.") for eid in entity_registry_ids)
    assert any(eid.startswith("binary_sensor.") for eid in entity_registry_ids)


@pytest.mark.asyncio
async def test_async_unload_entry_clears_hass_data(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Unloading the entry removes its bundle from hass.data[DOMAIN]."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        # Sanity: the entry is stored.
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_async_reload_entry_refreshes_state(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Reloading the entry tears down and brings the integration back up cleanly."""
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        first_bundle = hass.data[DOMAIN][mock_config_entry.entry_id]

        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        second_bundle = hass.data[DOMAIN][mock_config_entry.entry_id]

    # After reload, the bundle is freshly created — the previous one is gone.
    assert second_bundle is not first_bundle
    assert second_bundle["real_data"].data is mock_plant_data


# ─────────────────────────────────────────────────────────────────────────────
# Migration tests (PR #6c) — async_migrate_entry traverses sequential `if`
# blocks, NOT chained `elif`, so a v1.0 entry hits BOTH migrations in one call.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_migration_v1_2_to_v1_3_injects_default_factors(hass: HomeAssistant) -> None:
    """An entry already on minor_version=2 gains the CO2/tree factor defaults."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        data={"host": "192.0.2.1", "port": 502, "unit_id": 1},
        options={"scan_interval_real_data": 60},
        unique_id="DTUPRO-V12",
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.minor_version == 3
    assert entry.options[CONF_CO2_FACTOR_KG_PER_KWH] == DEFAULT_CO2_FACTOR_KG_PER_KWH
    assert entry.options[CONF_TREE_KG_CO2_PER_YEAR] == DEFAULT_TREE_KG_CO2_PER_YEAR
    # Existing options untouched.
    assert entry.options["scan_interval_real_data"] == 60


@pytest.mark.asyncio
async def test_migration_v1_0_traverses_to_v1_3_in_one_call(hass: HomeAssistant) -> None:
    """A very old v1.0 entry must reach v1.3 in a single migrate call.

    This locks in the sequential-`if` (vs chained `elif`) pattern: each branch
    must be an independent test on the bumped version, so the v1.2->v1.3 step
    fires immediately after the v1.1->v1.2 step within the same invocation.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        data={
            "host": "192.0.2.1",
            "port": 502,
            "unit_id": 1,
            CONF_SCAN_INTERVAL_REAL_DATA: 90,  # legacy location, must be moved to options
        },
        options={},
        unique_id="DTUPRO-V10",
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    # Both migrations must have applied.
    assert entry.minor_version == 3
    # v1.2 step: scan_interval moved from data to options.
    assert CONF_SCAN_INTERVAL_REAL_DATA not in entry.data
    assert entry.options[CONF_SCAN_INTERVAL_REAL_DATA] == 90
    # v1.3 step: factors injected.
    assert entry.options[CONF_CO2_FACTOR_KG_PER_KWH] == DEFAULT_CO2_FACTOR_KG_PER_KWH
    assert entry.options[CONF_TREE_KG_CO2_PER_YEAR] == DEFAULT_TREE_KG_CO2_PER_YEAR


@pytest.mark.asyncio
async def test_migration_v1_3_existing_factors_preserved(hass: HomeAssistant) -> None:
    """Re-running migration on an entry already at v1.3 with custom factors keeps them."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=3,
        data={"host": "192.0.2.1", "port": 502, "unit_id": 1},
        options={
            CONF_CO2_FACTOR_KG_PER_KWH: 0.053,  # user customised to RTE France
            CONF_TREE_KG_CO2_PER_YEAR: 25.0,
        },
        unique_id="DTUPRO-V13",
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    # No version bump (already at the latest).
    assert entry.minor_version == 3
    # Custom values preserved (setdefault is a no-op when the key exists).
    assert entry.options[CONF_CO2_FACTOR_KG_PER_KWH] == 0.053
    assert entry.options[CONF_TREE_KG_CO2_PER_YEAR] == 25.0
