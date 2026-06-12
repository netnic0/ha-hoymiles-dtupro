"""Config flow for the Hoymiles DTU-Pro integration.

Implements:
  * `async_step_user` — initial setup, with connectivity probe (D8: unique_id = DTU SN).
  * `async_step_reconfigure` — change host/port without dropping the entry.
  * `OptionsFlowHandler` — post-install user-tunable options (PR #4).

The schema migration (`async_migrate_entry`) lives in the package
`__init__.py` where HA discovers it automatically.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries

from .api import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_S,
    DEFAULT_UNIT_ID,
    HoymilesAsyncClient,
    HoymilesError,
)
from .const import (
    CONF_BACKOFF_INITIAL_S,
    CONF_BACKOFF_MAX_S,
    CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
    CONF_HOST,
    CONF_INVERTER_OFFLINE_THRESHOLD_H,
    CONF_PORT,
    CONF_RETRY_ATTEMPTS,
    CONF_SCAN_INTERVAL_METADATA,
    CONF_SCAN_INTERVAL_REAL_DATA,
    CONF_TIMEOUT_S,
    CONF_UNIT_ID,
    DEFAULT_BACKOFF_INITIAL_S,
    DEFAULT_BACKOFF_MAX_S,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_SCAN_INTERVAL_METADATA,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
    DOMAIN,
    ISSUE_DTU_UNREACHABLE_THRESHOLD,
    ISSUE_INVERTER_OFFLINE_THRESHOLD,
    OPTIONS_BACKOFF_INITIAL_MAX,
    OPTIONS_BACKOFF_INITIAL_MIN,
    OPTIONS_BACKOFF_MAX_MAX,
    OPTIONS_BACKOFF_MAX_MIN,
    OPTIONS_DTU_UNREACHABLE_MIN_MAX,
    OPTIONS_DTU_UNREACHABLE_MIN_MIN,
    OPTIONS_INVERTER_OFFLINE_H_MAX,
    OPTIONS_INVERTER_OFFLINE_H_MIN,
    OPTIONS_RETRY_ATTEMPTS_MAX,
    OPTIONS_RETRY_ATTEMPTS_MIN,
    OPTIONS_SCAN_INTERVAL_METADATA_MAX,
    OPTIONS_SCAN_INTERVAL_METADATA_MIN,
    OPTIONS_SCAN_INTERVAL_REAL_DATA_MAX,
    OPTIONS_SCAN_INTERVAL_REAL_DATA_MIN,
    OPTIONS_TIMEOUT_MAX,
    OPTIONS_TIMEOUT_MIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry, ConfigFlowResult

_LOGGER = logging.getLogger(__name__)

# ─── Initial setup schema (entry.data — host/port/unit_id only) ──────────────
# `scan_interval_real_data` moved to entry.options in MINOR_VERSION 2 (PR #4).
USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
    }
)


async def _probe_dtu(host: str, port: int, unit_id: int) -> str:
    """Open a Modbus connection, read the DTU serial, and close. Returns the SN."""
    client = HoymilesAsyncClient(host=host, port=port, unit_id=unit_id, timeout=DEFAULT_TIMEOUT_S)
    return await client.async_get_dtu_serial()


def _build_options_schema(current: dict[str, Any]) -> vol.Schema:
    """Build the OptionsFlow voluptuous schema, pre-filled with current values.

    `current` is `dict(entry.options)` falling back to integration defaults
    when a key is missing (first-time use of OptionsFlow on an existing entry).
    """
    return vol.Schema(
        {
            vol.Optional(
                CONF_SCAN_INTERVAL_REAL_DATA,
                default=current.get(
                    CONF_SCAN_INTERVAL_REAL_DATA,
                    int(DEFAULT_SCAN_INTERVAL_REAL_DATA.total_seconds()),
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=OPTIONS_SCAN_INTERVAL_REAL_DATA_MIN,
                    max=OPTIONS_SCAN_INTERVAL_REAL_DATA_MAX,
                ),
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_METADATA,
                default=current.get(
                    CONF_SCAN_INTERVAL_METADATA,
                    int(DEFAULT_SCAN_INTERVAL_METADATA.total_seconds()),
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=OPTIONS_SCAN_INTERVAL_METADATA_MIN,
                    max=OPTIONS_SCAN_INTERVAL_METADATA_MAX,
                ),
            ),
            vol.Optional(
                CONF_TIMEOUT_S,
                default=current.get(CONF_TIMEOUT_S, DEFAULT_TIMEOUT_S),
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=OPTIONS_TIMEOUT_MIN, max=OPTIONS_TIMEOUT_MAX),
            ),
            vol.Optional(
                CONF_RETRY_ATTEMPTS,
                default=current.get(CONF_RETRY_ATTEMPTS, DEFAULT_RETRY_ATTEMPTS),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=OPTIONS_RETRY_ATTEMPTS_MIN, max=OPTIONS_RETRY_ATTEMPTS_MAX),
            ),
            vol.Optional(
                CONF_BACKOFF_INITIAL_S,
                default=current.get(CONF_BACKOFF_INITIAL_S, DEFAULT_BACKOFF_INITIAL_S),
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=OPTIONS_BACKOFF_INITIAL_MIN, max=OPTIONS_BACKOFF_INITIAL_MAX),
            ),
            vol.Optional(
                CONF_BACKOFF_MAX_S,
                default=current.get(CONF_BACKOFF_MAX_S, DEFAULT_BACKOFF_MAX_S),
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=OPTIONS_BACKOFF_MAX_MIN, max=OPTIONS_BACKOFF_MAX_MAX),
            ),
            vol.Optional(
                CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
                default=current.get(
                    CONF_DTU_UNREACHABLE_THRESHOLD_MIN,
                    int(ISSUE_DTU_UNREACHABLE_THRESHOLD.total_seconds() // 60),
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=OPTIONS_DTU_UNREACHABLE_MIN_MIN, max=OPTIONS_DTU_UNREACHABLE_MIN_MAX),
            ),
            vol.Optional(
                CONF_INVERTER_OFFLINE_THRESHOLD_H,
                default=current.get(
                    CONF_INVERTER_OFFLINE_THRESHOLD_H,
                    int(ISSUE_INVERTER_OFFLINE_THRESHOLD.total_seconds() // 3600),
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=OPTIONS_INVERTER_OFFLINE_H_MIN, max=OPTIONS_INVERTER_OFFLINE_H_MAX),
            ),
        }
    )


def _validate_backoff_pair(values: dict[str, Any]) -> str | None:
    """Cross-field check: backoff_initial_s must be <= backoff_max_s.

    Returns an error key for the form, or None if valid.
    """
    initial = values.get(CONF_BACKOFF_INITIAL_S, DEFAULT_BACKOFF_INITIAL_S)
    upper = values.get(CONF_BACKOFF_MAX_S, DEFAULT_BACKOFF_MAX_S)
    if initial > upper:
        return "backoff_initial_above_max"
    return None


class HoymilesDtuProConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the user-driven config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                dtu_sn = await _probe_dtu(
                    user_input[CONF_HOST],
                    user_input.get(CONF_PORT, DEFAULT_PORT),
                    user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
                )
            except HoymilesError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during DTU probe")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(dtu_sn)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Hoymiles DTU-Pro ({dtu_sn})",
                    data=user_input,
                )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                dtu_sn = await _probe_dtu(
                    user_input[CONF_HOST],
                    user_input.get(CONF_PORT, DEFAULT_PORT),
                    user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
                )
            except HoymilesError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during DTU reconfigure probe")
                errors["base"] = "unknown"
            else:
                if dtu_sn != entry.unique_id:
                    return self.async_abort(reason="another_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data=user_input,
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Hook used by HA to construct the OptionsFlow handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Post-install user-tunable options for the integration (PR #4).

    Exposes 8 knobs: 2 scan intervals + 4 client (timeout, retries, backoff) +
    2 Repair Issue thresholds. All are read by `async_setup_entry` at load time
    via `entry.options.get(KEY, DEFAULT)`. An update listener triggers a reload
    whenever the user submits new values.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_backoff_pair(user_input)
            if err is not None:
                errors["base"] = err
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(dict(self.config_entry.options)),
            errors=errors,
        )
