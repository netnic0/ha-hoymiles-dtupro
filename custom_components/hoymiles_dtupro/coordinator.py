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
from datetime import date, datetime, timedelta
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

# Maximum plausible plant-level `today_production` increment between two
# consecutive polls, in watt-hours. Used by `TodayCache` to reject obvious
# glitches (e.g. uint16 overflow surfacing as 65535) without rejecting real
# production bursts.
#
# Theoretical upper bound for a 7-inverter plant (HMS-1000-2T, two MPPTs of
# up to ~550 W each) at a 10-minute poll interval:
#     7 x 2 x 550 W x 600 s / 3600 = ~1.28 kWh
# We use 10x margin over the realistic per-poll increment (~90 Wh at default
# 60s cadence) to keep the cap defensive against bogus values while never
# rejecting legitimate production. Module-private — not a user-tunable knob.
_MAX_SINGLE_POLL_WH_INCREMENT: int = 1_000


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
        dtu_unreachable_threshold: timedelta = ISSUE_DTU_UNREACHABLE_THRESHOLD,
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
        self._dtu_unreachable_threshold = dtu_unreachable_threshold
        # RF-flap-resilient cache for plant-level today_production. Fed on every
        # successful poll; read by HoymilesPlantSensor (today_production key) and
        # by HoymilesEnvironmentalSensor (CO2 / equivalent-trees-today derived
        # values). See `TodayCache` for the contract.
        self._today_cache = TodayCache()

    @property
    def issue_id(self) -> str:
        """Stable Repair Issue ID, scoped per config entry."""
        return f"{ISSUE_ID_DTU_UNREACHABLE}_{self._entry_id}"

    @property
    def plant_today_production_clamped(self) -> int | None:
        """Monotone, glitch-resistant plant `today_production` in watt-hours.

        Returns the last value fed to the cache (None until the first successful
        poll). Sensors should read this property instead of `data.today_production`
        to avoid surfacing RF-flap-induced drops to HA's recorder.
        """
        return self._today_cache.value

    async def _async_update_data(self) -> PlantData:
        try:
            data = await self._client.async_get_plant_data()
        except HoymilesError as err:
            self._maybe_raise_dtu_unreachable_issue()
            raise UpdateFailed(f"Hoymiles real-data fetch failed: {err}") from err

        # Feed the cache from the raw plant sum BEFORE clearing the dtu_unreachable
        # issue — the order is not semantically meaningful, but doing it first
        # keeps the data-side effects together and the HA-side effects together.
        self._today_cache.update(data.today_production)

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
        if elapsed < self._dtu_unreachable_threshold:
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
        inverter_offline_threshold: timedelta = ISSUE_INVERTER_OFFLINE_THRESHOLD,
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
        self._inverter_offline_threshold = inverter_offline_threshold
        # Keyed by inverter serial. Resets on integration reload — accepted
        # trade-off: the threshold timer restarts on reload, which is consistent with
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

            if now - last_seen < self._inverter_offline_threshold:
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


class TodayCache:
    """Monotone in-memory cache for the plant-level `today_production` (Wh).

    Why this exists
    ---------------
    The raw plant sum (`PlantData.today_production`) only includes inverters
    whose `link_status` is currently True. When one inverter's RF link flaps
    for a single poll cycle it disappears from `online_inverters`, the plant
    sum drops, and recovers next cycle. With sub-minute polling on a 7-inverter
    plant this happens 30-50x per day. Home Assistant's recorder treats each
    drop on a `state_class=TOTAL_INCREASING` sensor as a counter reset and
    credits the pre-drop delta to the cumulative — snowballing daily energy
    by an order of magnitude in the Energy dashboard.

    Contract
    --------
    `update(raw_wh, now=None)` returns a value that is:
      * Monotone within the same local date — never decreases vs the previous
        cached value, even if a transient RF flap drops the raw sum.
      * Reset to the new raw reading on local-midnight rollover (uses
        `dt_util.now()` so it honours the HA timezone, including DST).
      * Glitch-resistant — increments larger than `_MAX_SINGLE_POLL_WH_INCREMENT`
        are treated as bogus (e.g. uint16 overflow) and the previous cached
        value is returned instead.

    The cache is intentionally in-memory only: a fresh HA restart re-establishes
    the baseline from the first successful poll. The DTU itself owns the
    authoritative daily counter, so we never need to persist state.
    """

    def __init__(self) -> None:
        self._value_wh: int | None = None
        self._date: date | None = None

    @property
    def value(self) -> int | None:
        """Last cached value in watt-hours, or None before the first update."""
        return self._value_wh

    @property
    def cached_date(self) -> date | None:
        """Local date the cached value belongs to, or None before first update."""
        return self._date

    def update(self, raw_wh: int, *, now: datetime | None = None) -> int:
        """Feed a new raw plant reading and return the monotone-clamped value.

        Parameters
        ----------
        raw_wh
            Raw plant-level `today_production` in watt-hours (typically
            `plant_data.today_production`). Must be a non-negative integer.
        now
            Optional override for "now" — used only by tests. Production code
            should leave it as None so the cache reads `dt_util.now()` itself.

        Returns
        -------
        int
            The value the sensor should expose: monotone within the day,
            reset at midnight, glitch-resistant.
        """
        if raw_wh < 0:
            raise ValueError(f"raw_wh cannot be negative, got {raw_wh}")

        moment = now if now is not None else dt_util.now()
        today = moment.date()

        # Midnight rollover (or first call ever) → trust the raw reading as the
        # new baseline. We deliberately do NOT inherit yesterday's clamp because
        # the DTU resets `today_wh` at its own local midnight.
        if self._date != today or self._value_wh is None:
            self._value_wh = raw_wh
            self._date = today
            return raw_wh

        previous = self._value_wh

        # Drop: RF-flap or transient exclusion of an inverter from the sum.
        # Hold the previous (higher) value until the missing inverter returns.
        if raw_wh < previous:
            return previous

        # Glitch: implausible single-poll jump. Treat as garbage and hold.
        # Common cause: uint16 today_wh briefly surfaces with stale bits.
        if raw_wh - previous > _MAX_SINGLE_POLL_WH_INCREMENT:
            _LOGGER.warning(
                "today_production jumped from %d Wh to %d Wh in one poll "
                "(> %d Wh threshold) — holding previous value as a glitch guard",
                previous,
                raw_wh,
                _MAX_SINGLE_POLL_WH_INCREMENT,
            )
            return previous

        # Normal monotone progression.
        self._value_wh = raw_wh
        return raw_wh

    def reset(self) -> None:
        """Forget the cached value (used by tests; production rarely needs it)."""
        self._value_wh = None
        self._date = None
