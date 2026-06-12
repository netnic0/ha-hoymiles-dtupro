"""Tests for the OptionsFlow + async_migrate_entry (PR #4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import voluptuous as vol

from custom_components.hoymiles_dtupro import async_migrate_entry
from custom_components.hoymiles_dtupro.const import (
    CONF_BACKOFF_INITIAL_S,
    CONF_BACKOFF_MAX_S,
    CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
    CONF_INVERTER_OFFLINE_THRESHOLD_H,
    CONF_RETRY_ATTEMPTS,
    CONF_SCAN_INTERVAL_METADATA,
    CONF_SCAN_INTERVAL_REAL_DATA,
    CONF_TIMEOUT_S,
    DOMAIN,
)

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry


pytest_plugins = ["pytest_homeassistant_custom_component"]


# ─── Migration v1.1 → v1.2 ────────────────────────────────────────────────


async def test_migrate_v1_1_moves_scan_interval_to_options(
    hass, mock_config_entry_v1_legacy: MockConfigEntry
) -> None:
    """Entry at minor_version=1 with scan_interval_real_data in data is migrated
    so the key lives in options and minor_version becomes 2."""
    mock_config_entry_v1_legacy.add_to_hass(hass)

    result = await async_migrate_entry(hass, mock_config_entry_v1_legacy)

    assert result is True
    assert mock_config_entry_v1_legacy.minor_version == 2
    assert CONF_SCAN_INTERVAL_REAL_DATA not in mock_config_entry_v1_legacy.data
    assert mock_config_entry_v1_legacy.options[CONF_SCAN_INTERVAL_REAL_DATA] == 30


async def test_migrate_already_v1_2_is_noop(hass, mock_config_entry: MockConfigEntry) -> None:
    """Entry already at minor_version=2 is left untouched."""
    mock_config_entry.add_to_hass(hass)
    original_data = dict(mock_config_entry.data)
    original_options = dict(mock_config_entry.options)

    result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.minor_version == 2
    assert dict(mock_config_entry.data) == original_data
    assert dict(mock_config_entry.options) == original_options


async def test_migrate_v1_1_without_scan_interval_does_not_set_key(
    hass, mock_dtu_serial: str
) -> None:
    """If the legacy entry never carried scan_interval_real_data (theoretically
    impossible but defensively handled), the migration must not invent a value."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.1", "port": 502, "unit_id": 1},
        options={},
        unique_id=mock_dtu_serial,
        version=1,
        minor_version=1,
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == 2
    assert CONF_SCAN_INTERVAL_REAL_DATA not in entry.data
    assert CONF_SCAN_INTERVAL_REAL_DATA not in entry.options


# ─── OptionsFlow ──────────────────────────────────────────────────────────


async def test_options_flow_init_renders_form(hass, mock_config_entry: MockConfigEntry) -> None:
    """The init step shows the form with all 8 fields."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    schema_keys = {str(k) for k in result["data_schema"].schema}
    expected = {
        CONF_SCAN_INTERVAL_REAL_DATA,
        CONF_SCAN_INTERVAL_METADATA,
        CONF_TIMEOUT_S,
        CONF_RETRY_ATTEMPTS,
        CONF_BACKOFF_INITIAL_S,
        CONF_BACKOFF_MAX_S,
        CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
        CONF_INVERTER_OFFLINE_THRESHOLD_H,
    }
    assert expected <= schema_keys


async def test_options_flow_submit_valid_values_persists_options(
    hass, mock_config_entry: MockConfigEntry
) -> None:
    """Submitting valid values stores them in entry.options."""
    mock_config_entry.add_to_hass(hass)

    init = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    user_input = {
        CONF_SCAN_INTERVAL_REAL_DATA: 30,
        CONF_SCAN_INTERVAL_METADATA: 600,
        CONF_TIMEOUT_S: 8.0,
        CONF_RETRY_ATTEMPTS: 5,
        CONF_BACKOFF_INITIAL_S: 1.0,
        CONF_BACKOFF_MAX_S: 8.0,
        CONF_DTU_UNREACHABLE_THRESHOLD_MIN: 10,
        CONF_INVERTER_OFFLINE_THRESHOLD_H: 12,
    }
    result = await hass.config_entries.options.async_configure(
        init["flow_id"], user_input=user_input
    )

    assert result["type"] == "create_entry"
    assert result["data"] == user_input
    # entry.options reflects the new values once HA persists them.
    assert mock_config_entry.options[CONF_RETRY_ATTEMPTS] == 5
    assert mock_config_entry.options[CONF_BACKOFF_INITIAL_S] == 1.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (CONF_RETRY_ATTEMPTS, 0),  # below min
        (CONF_RETRY_ATTEMPTS, 100),  # above max
        (CONF_SCAN_INTERVAL_REAL_DATA, 5),  # below min (10)
        (CONF_TIMEOUT_S, 60.0),  # above max (30)
        (CONF_DTU_UNREACHABLE_THRESHOLD_MIN, 0),  # below min (1)
    ],
)
async def test_options_flow_rejects_out_of_range_values(
    hass, mock_config_entry: MockConfigEntry, field: str, value: float
) -> None:
    """Voluptuous range validation rejects out-of-bounds values."""
    mock_config_entry.add_to_hass(hass)
    init = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    user_input = {
        CONF_SCAN_INTERVAL_REAL_DATA: 60,
        CONF_SCAN_INTERVAL_METADATA: 300,
        CONF_TIMEOUT_S: 5.0,
        CONF_RETRY_ATTEMPTS: 3,
        CONF_BACKOFF_INITIAL_S: 0.5,
        CONF_BACKOFF_MAX_S: 4.0,
        CONF_DTU_UNREACHABLE_THRESHOLD_MIN: 5,
        CONF_INVERTER_OFFLINE_THRESHOLD_H: 6,
    }
    user_input[field] = value

    with pytest.raises(vol.Invalid):
        await hass.config_entries.options.async_configure(init["flow_id"], user_input=user_input)


async def test_options_flow_rejects_inverted_backoff_pair(
    hass, mock_config_entry: MockConfigEntry
) -> None:
    """Cross-field check: backoff_initial > backoff_max must fail with our
    custom error key."""
    mock_config_entry.add_to_hass(hass)
    init = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        init["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL_REAL_DATA: 60,
            CONF_SCAN_INTERVAL_METADATA: 300,
            CONF_TIMEOUT_S: 5.0,
            CONF_RETRY_ATTEMPTS: 3,
            CONF_BACKOFF_INITIAL_S: 4.0,  # > backoff_max
            CONF_BACKOFF_MAX_S: 2.0,
            CONF_DTU_UNREACHABLE_THRESHOLD_MIN: 5,
            CONF_INVERTER_OFFLINE_THRESHOLD_H: 6,
        },
    )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "backoff_initial_above_max"}
