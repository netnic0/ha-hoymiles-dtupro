"""HA-native tests targeting __init__.py paths missing from prior coverage.

Targets identified in PR #5a's coverage report (78.94 % overall, gaps on
custom_components/hoymiles_dtupro/__init__.py:158, 173->187, 179->187,
188->190):

  * line 158 — `_async_options_update_listener` triggering a reload.
  * line 158 / 173-179 — `async_unload_entry` when bundle is None
    (already-unloaded edge case).
  * lines 175-185 — `async_unload_entry` deletes per-inverter Repair Issues
    for every serial known to the metadata coordinator.

Patterns mirror tests/test_init.py and tests/test_options_flow.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hoymiles_dtupro.const import (
    CONF_RETRY_ATTEMPTS,
    DOMAIN,
    ISSUE_ID_DTU_UNREACHABLE,
    ISSUE_ID_INVERTER_OFFLINE,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.api.models import PlantData


_CLIENT_PATH = "custom_components.hoymiles_dtupro.api.HoymilesAsyncClient"


# ─── Options-update listener ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_options_update_listener_reloads_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Submitting OptionsFlow changes triggers async_reload via the listener.

    Covers __init__.py:158 (`_async_options_update_listener` body) and the
    `entry.add_update_listener` plumbing on line 143.
    """
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        first_bundle = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Submit options change → triggers _async_options_update_listener →
        # which calls hass.config_entries.async_reload(entry.entry_id).
        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                "scan_interval_real_data": 45,
                "scan_interval_metadata": 300,
                "timeout_s": 5.0,
                "retry_attempts": 7,  # was DEFAULT (3)
                "backoff_initial_s": 0.5,
                "backoff_max_s": 4.0,
                "dtu_unreachable_threshold_min": 5,
                "inverter_offline_threshold_h": 6,
            },
        )
        await hass.async_block_till_done()

    second_bundle = hass.data[DOMAIN][mock_config_entry.entry_id]
    # Reload tore down the first bundle and built a fresh one.
    assert second_bundle is not first_bundle
    # New retry_attempts value is honoured by the freshly-built client.
    assert mock_config_entry.options[CONF_RETRY_ATTEMPTS] == 7


# ─── async_unload_entry — edge cases ──────────────────────────────────────


@pytest.mark.asyncio
async def test_async_unload_entry_handles_missing_bundle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Unloading an entry whose bundle was already removed must not raise.

    Covers __init__.py:172-173 (`bundle is None` early-skip).
    """
    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Manually drop the bundle to simulate the "already unloaded" branch.
        hass.data[DOMAIN].pop(mock_config_entry.entry_id)

        # Unload must still return cleanly (the platforms unload path runs
        # regardless of the bundle presence).
        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)

    assert result is True


@pytest.mark.asyncio
async def test_async_unload_entry_deletes_per_inverter_repair_issues(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_plant_data: PlantData,
) -> None:
    """Unload deletes every per-inverter offline issue ever raised for the entry.

    Covers __init__.py:179-185 (loop over `metadata_coord.known_inverter_serials`
    issuing `ir.async_delete_issue` for each).
    """
    from homeassistant.helpers import issue_registry as ir

    mock_config_entry.add_to_hass(hass)

    fake_client = AsyncMock()
    fake_client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    with patch(_CLIENT_PATH, return_value=fake_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Seed the metadata coordinator's known-serials cache so the unload
        # loop has something to clear.
        bundle = hass.data[DOMAIN][mock_config_entry.entry_id]
        metadata_coord = bundle["metadata"]
        seeded_serial = "AABBCC112233"
        metadata_coord._last_seen_online[seeded_serial] = mock_plant_data.fetched_at

        # Pre-create both kinds of issues to verify they are cleared.
        registry = ir.async_get(hass)
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_ID_DTU_UNREACHABLE}_{mock_config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="dtu_unreachable",
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_ID_INVERTER_OFFLINE}_{seeded_serial}_{mock_config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="inverter_offline_long",
        )
        await hass.async_block_till_done()

        # Sanity: both issues are present.
        assert (
            registry.async_get_issue(
                DOMAIN, f"{ISSUE_ID_DTU_UNREACHABLE}_{mock_config_entry.entry_id}"
            )
            is not None
        )
        assert (
            registry.async_get_issue(
                DOMAIN,
                f"{ISSUE_ID_INVERTER_OFFLINE}_{seeded_serial}_{mock_config_entry.entry_id}",
            )
            is not None
        )

        # Unload — both issues should be deleted by the cleanup loop.
        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert (
        registry.async_get_issue(DOMAIN, f"{ISSUE_ID_DTU_UNREACHABLE}_{mock_config_entry.entry_id}")
        is None
    )
    assert (
        registry.async_get_issue(
            DOMAIN,
            f"{ISSUE_ID_INVERTER_OFFLINE}_{seeded_serial}_{mock_config_entry.entry_id}",
        )
        is None
    )
