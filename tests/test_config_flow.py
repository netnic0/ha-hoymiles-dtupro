"""HA-native tests for the Hoymiles DTU-Pro config flow.

These tests need pytest-homeassistant-custom-component installed and use the
``hass`` and ``enable_custom_integrations`` fixtures provided by it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from custom_components.hoymiles_dtupro.api.exceptions import HoymilesConnectionError
from custom_components.hoymiles_dtupro.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


# Path used to patch the connectivity probe (one place, several tests).
_PROBE_PATH = "custom_components.hoymiles_dtupro.config_flow._probe_dtu"


@pytest.mark.asyncio
async def test_user_step_creates_entry_on_success(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_dtu_serial: str,
) -> None:
    """Happy path: probe succeeds, entry is created with DTU SN as unique_id."""
    user_input = {
        "host": "192.0.2.1",
        "port": 502,
        "unit_id": 1,
    }

    with patch(_PROBE_PATH, return_value=mock_dtu_serial):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "create_entry"
    assert result2["title"] == f"Hoymiles DTU-Pro ({mock_dtu_serial})"
    assert result2["data"] == user_input
    # The Config Flow stamps unique_id on the entry it creates.
    assert result2["result"].unique_id == mock_dtu_serial


@pytest.mark.asyncio
async def test_user_step_shows_cannot_connect_on_hoymiles_connection_error(
    hass: HomeAssistant,
    enable_custom_integrations,
) -> None:
    """When the probe raises HoymilesError, the form re-displays with cannot_connect."""
    user_input = {"host": "192.0.2.99", "port": 502, "unit_id": 1}

    with patch(_PROBE_PATH, side_effect=HoymilesConnectionError("nope")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "form"
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_user_step_shows_unknown_on_unexpected_exception(
    hass: HomeAssistant,
    enable_custom_integrations,
) -> None:
    """A non-Hoymiles exception during probe surfaces as base=unknown."""
    user_input = {"host": "192.0.2.1", "port": 502, "unit_id": 1}

    with patch(_PROBE_PATH, side_effect=RuntimeError("boom")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}


@pytest.mark.asyncio
async def test_user_step_aborts_on_already_configured(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
    mock_dtu_serial: str,
) -> None:
    """Probing twice the same DTU (matching unique_id) aborts the second flow."""
    mock_config_entry.add_to_hass(hass)
    user_input = {"host": "192.0.2.1", "port": 502, "unit_id": 1}

    with patch(_PROBE_PATH, return_value=mock_dtu_serial):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "abort"
    assert result2["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_reconfigure_step_aborts_when_dtu_serial_changes(
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_config_entry: MockConfigEntry,
) -> None:
    """If the new host points to a different DTU, the reconfigure aborts to avoid mixing devices."""
    mock_config_entry.add_to_hass(hass)
    user_input = {"host": "192.0.2.2", "port": 502, "unit_id": 1}

    with patch(_PROBE_PATH, return_value="111122223333"):
        result = await mock_config_entry.start_reconfigure_flow(hass)
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)

    assert result2["type"] == "abort"
    assert result2["reason"] == "another_device"
