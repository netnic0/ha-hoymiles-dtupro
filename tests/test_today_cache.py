"""Pure unit tests for `TodayCache` (PR #7 — today_production RF-flap fix).

These tests do not need the `hass` fixture — `TodayCache` is a pure-Python
helper that takes a `now` override so we can drive it deterministically
across days and timezones.

Covered:
  * First update — establishes baseline from the raw reading.
  * Monotone clamp on drop — RF flap excludes one inverter, raw sum drops,
    cache holds previous value.
  * Persistent offline — same drop sustained across many polls keeps holding.
  * Recovery — raw catches up, cache advances again.
  * Midnight rollover — new local date trusts the new raw reading as baseline.
  * Glitch reject — implausible single-poll jump (uint16-style overflow)
    is treated as garbage and held.
  * DST fall-back — when a local date repeats one hour, the cache still
    reasonably monotone-clamps (no false reset on the repeated wall-clock).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.hoymiles_dtupro.coordinator import (
    _MAX_SINGLE_POLL_WH_INCREMENT,
    TodayCache,
)


def _at(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    """Build an aware UTC datetime — `TodayCache` only reads `.date()` from it."""
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def test_first_update_establishes_baseline_from_raw() -> None:
    """The very first update returns the raw reading unchanged."""
    cache = TodayCache()

    assert cache.value is None
    assert cache.cached_date is None

    result = cache.update(150, now=_at(2026, 6, 30, 8, 0))

    assert result == 150
    assert cache.value == 150
    assert cache.cached_date == _at(2026, 6, 30).date()


def test_monotone_progression_returns_raw_when_increasing() -> None:
    """Normal sun-rising sequence — increments under the glitch cap pass through."""
    cache = TodayCache()
    cache.update(100, now=_at(2026, 6, 30, 8, 0))

    assert cache.update(250, now=_at(2026, 6, 30, 8, 1)) == 250
    assert cache.update(420, now=_at(2026, 6, 30, 8, 2)) == 420
    assert cache.value == 420


def test_single_drop_holds_previous_value() -> None:
    """RF flap on one inverter for one poll → raw drops → cache holds."""
    cache = TodayCache()
    cache.update(800, now=_at(2026, 6, 30, 10, 0))

    # One inverter dropped from `online_inverters` this cycle — raw sum halves.
    result = cache.update(400, now=_at(2026, 6, 30, 10, 1))

    assert result == 800
    assert cache.value == 800


def test_drop_then_recovery_resumes_monotonic_advance() -> None:
    """Inverter rejoins next cycle — cache advances from the raw reading."""
    cache = TodayCache()
    cache.update(800, now=_at(2026, 6, 30, 10, 0))
    cache.update(400, now=_at(2026, 6, 30, 10, 1))  # flap

    # Raw recovers to or above the held value — cache advances.
    result = cache.update(850, now=_at(2026, 6, 30, 10, 2))

    assert result == 850
    assert cache.value == 850


def test_sustained_offline_inverter_keeps_holding_for_many_polls() -> None:
    """An inverter offline for the next 10 polls must not collapse the value."""
    cache = TodayCache()
    cache.update(1000, now=_at(2026, 6, 30, 12, 0))

    base = _at(2026, 6, 30, 12, 1)
    for i in range(10):
        result = cache.update(500, now=base + timedelta(minutes=i))
        assert result == 1000
        assert cache.value == 1000


def test_midnight_rollover_resets_baseline_to_new_raw() -> None:
    """At local midnight the DTU's `today_wh` resets — the cache must trust it."""
    cache = TodayCache()
    cache.update(8500, now=_at(2026, 6, 30, 23, 30))

    # New local day — DTU has reset to a small new-day reading.
    result = cache.update(20, now=_at(2026, 7, 1, 0, 5))

    assert result == 20
    assert cache.value == 20
    assert cache.cached_date == _at(2026, 7, 1).date()


def test_glitch_above_threshold_is_held_not_published() -> None:
    """A bogus uint16-style jump (e.g. 65535 Wh) must be rejected as garbage."""
    cache = TodayCache()
    cache.update(500, now=_at(2026, 6, 30, 14, 0))

    bogus = 500 + _MAX_SINGLE_POLL_WH_INCREMENT + 1
    result = cache.update(bogus, now=_at(2026, 6, 30, 14, 1))

    assert result == 500
    assert cache.value == 500


def test_glitch_exactly_at_threshold_is_accepted() -> None:
    """The cap is inclusive — a jump of exactly the threshold passes through.

    Pinning the boundary keeps the production-bound check (`> THRESHOLD`)
    explicit; future tightening would break this test deliberately.
    """
    cache = TodayCache()
    cache.update(500, now=_at(2026, 6, 30, 14, 0))

    at_cap = 500 + _MAX_SINGLE_POLL_WH_INCREMENT
    result = cache.update(at_cap, now=_at(2026, 6, 30, 14, 1))

    assert result == at_cap
    assert cache.value == at_cap


def test_negative_raw_reading_raises_value_error() -> None:
    """`today_production` is uint16 in the DTU — negatives indicate a bug upstream."""
    cache = TodayCache()

    with pytest.raises(ValueError, match="cannot be negative"):
        cache.update(-1, now=_at(2026, 6, 30))


def test_reset_clears_cached_state() -> None:
    """`reset()` makes the next `update` behave like the first one."""
    cache = TodayCache()
    cache.update(500, now=_at(2026, 6, 30))

    cache.reset()

    assert cache.value is None
    assert cache.cached_date is None
    assert cache.update(42, now=_at(2026, 6, 30, 12, 0)) == 42


def test_uses_dt_util_now_when_no_override_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production calls pass no `now` — verify it pulls from `dt_util.now()`."""
    from homeassistant.util import dt as dt_util

    fixed = datetime(2026, 6, 30, 9, 0, tzinfo=UTC)
    monkeypatch.setattr(dt_util, "now", lambda: fixed)

    cache = TodayCache()
    result = cache.update(123)

    assert result == 123
    assert cache.cached_date == fixed.date()


def test_dst_fall_back_does_not_falsely_reset() -> None:
    """On DST fall-back the wall clock repeats, but the LOCAL date does not.

    Cache uses `dt_util.now().date()` (a `date` object, no hour component),
    so DST transitions inside a day are invisible to the rollover check.
    """
    paris = ZoneInfo("Europe/Paris")
    # 2026-10-25 02:00 CEST → 02:00 CET (fall-back). Date stays 2026-10-25.
    before_fallback = datetime(2026, 10, 25, 1, 30, tzinfo=paris)
    after_fallback = datetime(2026, 10, 25, 2, 30, tzinfo=paris)

    assert before_fallback.date() == after_fallback.date()  # sanity

    cache = TodayCache()
    cache.update(5000, now=before_fallback)

    # An RF flap right around the transition must still hold the cached value.
    result = cache.update(2500, now=after_fallback)
    assert result == 5000
    assert cache.value == 5000


def test_dst_spring_forward_does_not_falsely_reset() -> None:
    """Spring-forward also stays inside the same local date — no reset."""
    paris = ZoneInfo("Europe/Paris")
    before_jump = datetime(2026, 3, 29, 1, 30, tzinfo=paris)
    after_jump = datetime(2026, 3, 29, 3, 30, tzinfo=paris)

    assert before_jump.date() == after_jump.date()

    cache = TodayCache()
    cache.update(300, now=before_jump)
    # Normal monotone progression across the jump — should pass through.
    assert cache.update(450, now=after_jump) == 450
