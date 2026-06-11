"""Data update coordinators for Hoymiles DTU-Pro (D6 + FC3).

Two coordinators share ONE `HoymilesAsyncClient` instance:
  * RealDataCoordinator — short interval (60s default) for live power/voltage/current.
  * MetadataCoordinator — long interval (5min default) for alarm_count, link_status,
    operating_status which rarely change.

The shared client serialises requests internally (asyncio.Lock) so the DTU
sees at most one outstanding Modbus query at a time.

Both coordinators inherit `TimestampDataUpdateCoordinator` so HA exposes
`last_update_success_time` natively — used by the Repair-Issues machinery
introduced in PR #2 to detect prolonged unreachability.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import HoymilesAsyncClient, HoymilesError, PlantData
from .const import (
    DEFAULT_SCAN_INTERVAL_METADATA,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
    DOMAIN,
    ISSUE_DTU_UNREACHABLE_THRESHOLD,
    ISSUE_ID_DTU_UNREACHABLE,
    ISSUE_ID_INVERTER_OFFLINE,
    ISSUE_INVERTER_OFFLINE_THRESHOLD,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class HoymilesRealDataCoordinator(TimestampDataUpdateCoordinator[PlantData]):
    """Polls live data (PV power, voltages, temperature) at short interval.

    Owns the `dtu_unreachable` Repair Issue lifecycle: fired when this
    coordinator has not had a successful update for more than
    `ISSUE_DTU_UNREACHABLE_THRESHOLD`; cleared on the next successful update.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: HoymilesAsyncClient,
        *,
        entry_id: str,
        host: str,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL_REAL_DATA,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Hoymiles DTU-Pro real data",
            update_interval=update_interval,
            always_update=False,
        )
        self._client = client
        self._entry_id = entry_id
        self._host = host

    @property
    def issue_id(self) -> str:
        """Stable Repair Issue ID, scoped per config entry."""
        return f"{ISSUE_ID_DTU_UNREACHABLE}_{self._entry_id}"

    async def _async_update_data(self) -> PlantData:
        try:
            data = await self._client.async_get_plant_data()
        except HoymilesError as err:
            self._maybe_raise_dtu_unreachable_issue()
            raise UpdateFailed(f"Hoymiles real-data fetch failed: {err}") from err

        # Successful poll → clear any pending dtu_unreachable issue.
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
        return data

    def _maybe_raise_dtu_unreachable_issue(self) -> None:
        """Fire `dtu_unreachable` once the DTU has been silent past the threshold.

        Granularity note: HA's `last_update_success_time` is the LAST SUCCESS
        timestamp. When the DTU is failing, `utcnow() - last_update_success_time`
        overstates the failure duration by up to one scan interval (the gap
        between the last successful poll and the first failed one). For a
        5-minute threshold and a 60-second poll cadence this off-by-one is
        negligible; document and accept.
        """
        last_ok = self.last_update_success_time
        if last_ok is None:
            # Never had a successful update — the integration is still booting
            # or the DTU has been unreachable from the very first try. Defer
            # to ConfigEntryNotReady semantics; do not raise an issue here.
            return

        elapsed = dt_util.utcnow() - last_ok
        if elapsed < ISSUE_DTU_UNREACHABLE_THRESHOLD:
            return

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_ID_DTU_UNREACHABLE,
            translation_placeholders={"host": self._host},
            learn_more_url="https://github.com/netnic0/ha-hoymiles-dtupro#troubleshooting",
        )


class HoymilesMetadataCoordinator(TimestampDataUpdateCoordinator[PlantData]):
    """Polls slow-changing data (link_status, alarm_count) at long interval.

    Owns the `inverter_offline_long` Repair Issue lifecycle: fired (per inverter
    serial) when an inverter has reported `link_status=False` continuously for
    more than `ISSUE_INVERTER_OFFLINE_THRESHOLD`. Guard: only inverters that
    have been observed online at least once since the integration started can
    raise the issue — this avoids false positives for new hardware that has
    yet to come online.

    Currently fetches the same `PlantData` payload as the real-data coordinator
    because the underlying Modbus query is the same. We keep the split because
    HA entities will subscribe to the appropriate coordinator and we may
    diverge the queries when DTU control endpoints (limit_persistent, etc.)
    are added later.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: HoymilesAsyncClient,
        *,
        entry_id: str,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL_METADATA,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Hoymiles DTU-Pro metadata",
            update_interval=update_interval,
            always_update=False,
        )
        self._client = client
        self._entry_id = entry_id
        # Keyed by inverter serial. Resets on integration reload — accepted
        # trade-off: the 6h timer restarts on reload, which is consistent with
        # `is_persistent=False` Repair Issues that already do not survive HA restart.
        self._last_seen_online: dict[str, datetime] = {}

    def inverter_issue_id(self, serial: str) -> str:
        """Stable Repair Issue ID for a given inverter, scoped per config entry."""
        return f"{ISSUE_ID_INVERTER_OFFLINE}_{serial}_{self._entry_id}"

    @property
    def known_inverter_serials(self) -> tuple[str, ...]:
        """Serials we have ever seen online — used by `async_unload_entry` for cleanup."""
        return tuple(self._last_seen_online)

    async def _async_update_data(self) -> PlantData:
        try:
            data = await self._client.async_get_plant_data()
        except HoymilesError as err:
            raise UpdateFailed(f"Hoymiles metadata fetch failed: {err}") from err

        self._evaluate_inverter_offline_issues(data)
        return data

    def _evaluate_inverter_offline_issues(self, data: PlantData) -> None:
        """Run the create/clear cycle for `inverter_offline_long` on every poll."""
        now = dt_util.utcnow()
        # Deduplicate inverters by serial — each HMS-1000-2T appears twice (one
        # entry per MPPT port) but the link_status is identical at the inverter
        # level, so we only need to evaluate the first occurrence per serial.
        seen_serials: set[str] = set()
        for inv in data.inverters:
            serial = inv.serial_number
            if serial in seen_serials:
                continue
            seen_serials.add(serial)

            if inv.link_status:
                # Online → record sighting and clear any existing issue.
                self._last_seen_online[serial] = now
                ir.async_delete_issue(self.hass, DOMAIN, self.inverter_issue_id(serial))
                continue

            # Offline. Only meaningful if the inverter was once seen online.
            last_seen = self._last_seen_online.get(serial)
            if last_seen is None:
                # Never seen online since this integration load — do nothing.
                continue

            if now - last_seen < ISSUE_INVERTER_OFFLINE_THRESHOLD:
                # Within tolerance window — also clear any stale issue from
                # a previous longer-than-threshold gap that has since resumed.
                ir.async_delete_issue(self.hass, DOMAIN, self.inverter_issue_id(serial))
                continue

            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self.inverter_issue_id(serial),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_ID_INVERTER_OFFLINE,
                translation_placeholders={"serial": serial},
            )
