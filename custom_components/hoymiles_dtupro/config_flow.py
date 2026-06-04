"""Config flow for the Hoymiles DTU-Pro integration.

Implements:
  * `async_step_user` — initial setup, with connectivity probe (D8: unique_id = DTU SN).
  * `async_step_reconfigure` — change host/port without dropping the entry.

Skeleton only — full HA-native testing requires `pytest-homeassistant-custom-component`,
which is out of scope for this PoC (see plan-review FI4).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from ha_hoymiles_dtupro import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_S,
    DEFAULT_UNIT_ID,
    HoymilesAsyncClient,
    HoymilesError,
)

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL_REAL_DATA,
    CONF_UNIT_ID,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
    DOMAIN,
    MIN_SCAN_INTERVAL_SECONDS,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.config_entries import ConfigFlowResult

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(
            CONF_SCAN_INTERVAL_REAL_DATA,
            default=int(DEFAULT_SCAN_INTERVAL_REAL_DATA.total_seconds()),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS)),
    }
)


async def _probe_dtu(host: str, port: int, unit_id: int) -> str:
    """Open a Modbus connection, read the DTU serial, and close. Returns the SN."""
    client = HoymilesAsyncClient(
        host=host, port=port, unit_id=unit_id, timeout=DEFAULT_TIMEOUT_S
    )
    return await client.async_get_dtu_serial()


# Importing HA at module level breaks the PoC's offline tests; we defer.
try:  # pragma: no cover - exercised only inside HA
    from homeassistant import config_entries

    class HoymilesDtuProConfigFlow(  # type: ignore[misc]
        config_entries.ConfigFlow, domain=DOMAIN
    ):
        """Handle the user-driven config flow."""

        VERSION = 1
        MINOR_VERSION = 1

        async def async_step_user(
            self, user_input: dict[str, Any] | None = None
        ) -> ConfigFlowResult:
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
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error during DTU probe")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(dtu_sn)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Hoymiles DTU-Pro ({dtu_sn})",
                        data=user_input,
                    )

            return self.async_show_form(
                step_id="user", data_schema=USER_SCHEMA, errors=errors
            )

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
                except Exception:  # noqa: BLE001
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

except ImportError:  # pragma: no cover - PoC offline path
    _LOGGER.debug("Home Assistant runtime unavailable, ConfigFlow stub kept disabled")
