"""HA-native coverage tests for error paths missing from prior coverage.

Targets identified in PR #5a's coverage report:

  * coordinator.py:178-179 — HoymilesMetadataCoordinator._async_update_data
    raises UpdateFailed when the underlying client raises HoymilesError.
  * config_flow.py:238-239 — async_step_reconfigure cannot_connect branch
    on HoymilesError.
  * config_flow.py:240-242 — async_step_reconfigure unknown branch on
    arbitrary Exception.
  * config_flow.py:246-250 — async_step_reconfigure happy path
    (update_reload_and_abort) when the DTU SN matches the entry.

Patterns mirror tests/test_coordinator.py and tests/test_config_flow.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hoymiles_dtupro.api.client import HoymilesAsyncClient
from custom_components.hoymiles_dtupro.api.exceptions import HoymilesConnectionError
from custom_components.hoymiles_dtupro.coordinator import HoymilesMetadataCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


# Patch target re-used across the reconfigure tests below.
_PROBE_PATH = "custom_components.hoymiles_dtupro.config_flow._probe_dtu"


# ─── Coordinator error path ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metadata_coordinator_raises_update_failed_on_hoymiles_error(
    hass: HomeAssistant,
) -> None:
    """The metadata coordinator wraps HoymilesError into UpdateFailed.

    Covers coordinator.py:178-179 (the `except HoymilesError → raise
    UpdateFailed(...) from err` branch). HA depends on UpdateFailed to
    schedule its own retry/backoff so this is a contract-level guarantee.
    """
    from homeassistant.helpers.update_coordinator import UpdateFailed

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(side_effect=HoymilesConnectionError("DTU offline"))

    coord = HoymilesMetadataCoordinator(hass, client, entry_id="test_entry")

    # async_refresh swallows UpdateFailed but stores the exception. We force
    # the branch via the private _async_update_data helper to assert the
    # raise + cause chain directly.
    with pytest.raises(UpdateFailed) as exc_info:
        await coord._async_update_data()

    assert "Hoymiles metadata fetch failed" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, HoymilesConnectionError)


# ─── Reconfigure flow error paths ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconfigure_step_shows_cannot_connect_on_hoymiles_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfigure surfaces base=cannot_connect when the probe raises HoymilesError.

    Covers config_flow.py:238-239 (the `except HoymilesError` branch in
    `async_step_reconfigure`). Mirrors the equivalent user-step test.
    """
    mock_config_entry.add_to_hass(hass)
    user_input = {"host": "192.0.2.99", "port": 502, "unit_id": 1}

    with patch(_PROBE_PATH, side_effect=HoymilesConnectionError("nope")):
        result = await mock_config_entry.start_reconfigure_flow(hass)
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "form"
    assert result2["step_id"] == "reconfigure"
    assert result2["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_reconfigure_step_shows_unknown_on_unexpected_exception(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfigure surfaces base=unknown when the probe raises a non-Hoymiles
    exception.

    Covers config_flow.py:240-242 (the bare `except Exception` branch with
    its accompanying `_LOGGER.exception(...)`).
    """
    mock_config_entry.add_to_hass(hass)
    user_input = {"host": "192.0.2.1", "port": 502, "unit_id": 1}

    with patch(_PROBE_PATH, side_effect=RuntimeError("boom")):
        result = await mock_config_entry.start_reconfigure_flow(hass)
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "form"
    assert result2["step_id"] == "reconfigure"
    assert result2["errors"] == {"base": "unknown"}


@pytest.mark.asyncio
async def test_reconfigure_step_updates_entry_on_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_dtu_serial: str,
) -> None:
    """Reconfigure with the same DTU SN updates entry.data and aborts with
    `reconfigure_successful`.

    Covers config_flow.py:243-250 (the `else: if dtu_sn != entry.unique_id`
    happy path). The "another_device" abort is already covered by
    test_config_flow.py.
    """
    mock_config_entry.add_to_hass(hass)
    new_input = {"host": "192.0.2.42", "port": 1502, "unit_id": 2}

    with patch(_PROBE_PATH, return_value=mock_dtu_serial):
        result = await mock_config_entry.start_reconfigure_flow(hass)
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], new_input)

    assert result2["type"] == "abort"
    assert result2["reason"] == "reconfigure_successful"
    # The entry's connection identity is updated.
    assert mock_config_entry.data["host"] == "192.0.2.42"
    assert mock_config_entry.data["port"] == 1502
    assert mock_config_entry.data["unit_id"] == 2
