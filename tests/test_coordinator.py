"""HA-native tests for the Hoymiles DTU-Pro coordinators.

Validates:
  * First refresh populates `coordinator.data` with the PlantData snapshot.
  * UpdateFailed is raised on HoymilesError (so HA retries with backoff).
  * Real-data and metadata coordinators share ONE underlying client (FC3).
  * Each coordinator's update_interval matches its declared default.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from custom_components.hoymiles_dtupro.api.client import HoymilesAsyncClient
from custom_components.hoymiles_dtupro.api.exceptions import HoymilesConnectionError
from custom_components.hoymiles_dtupro.const import (
    DEFAULT_SCAN_INTERVAL_METADATA,
    DEFAULT_SCAN_INTERVAL_REAL_DATA,
)
from custom_components.hoymiles_dtupro.coordinator import (
    HoymilesMetadataCoordinator,
    HoymilesRealDataCoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.hoymiles_dtupro.api.models import PlantData


@pytest.mark.asyncio
async def test_real_data_coordinator_first_refresh_populates_data(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """A successful first refresh stores the PlantData snapshot on the coordinator."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")
    await coord.async_refresh()

    assert coord.last_update_success is True
    assert coord.data is mock_plant_data
    client.async_get_plant_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_real_data_coordinator_raises_update_failed_on_hoymiles_error(
    hass: HomeAssistant,
) -> None:
    """A HoymilesError from the client must surface as UpdateFailed for HA backoff."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(side_effect=HoymilesConnectionError("nope"))

    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")
    with pytest.raises(UpdateFailed, match="real-data fetch failed"):
        await coord._async_update_data()


@pytest.mark.asyncio
async def test_real_data_and_metadata_share_one_client(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """FC3: a single client instance drives both coordinators (no duplicate sockets)."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    real = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")
    meta = HoymilesMetadataCoordinator(hass, client, entry_id="test_entry")

    await real.async_refresh()
    await meta.async_refresh()

    # Same underlying client object — proves the FC3 sharing contract.
    assert real._client is meta._client is client
    # Each coordinator made one fetch on the shared client.
    assert client.async_get_plant_data.await_count == 2


@pytest.mark.asyncio
async def test_coordinators_use_their_default_intervals(hass: HomeAssistant) -> None:
    """The two coordinators carry the documented default intervals (60s vs 5min)."""
    client = AsyncMock(spec=HoymilesAsyncClient)

    real = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")
    meta = HoymilesMetadataCoordinator(hass, client, entry_id="test_entry")

    assert real.update_interval == DEFAULT_SCAN_INTERVAL_REAL_DATA
    assert meta.update_interval == DEFAULT_SCAN_INTERVAL_METADATA == timedelta(minutes=5)
    # Sanity: the real-data interval is strictly shorter than the metadata interval.
    assert real.update_interval < meta.update_interval


# ─────────────────────────────────────────────────────────────────────────────
# Repair Issue lifecycle tests (PR #2)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metadata_records_serial_when_seen_online(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """Every online inverter is recorded in `_last_seen_online` after a successful poll."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    meta = HoymilesMetadataCoordinator(hass, client, entry_id="test_entry")
    await meta.async_refresh()

    # Every online inverter (deduplicated by serial) should now be tracked.
    online_serials = {inv.serial_number for inv in mock_plant_data.online_inverters}
    assert set(meta._last_seen_online.keys()) == online_serials
    # known_inverter_serials exposes the same set as a tuple for cleanup logic.
    assert set(meta.known_inverter_serials) == online_serials


@pytest.mark.asyncio
async def test_metadata_does_not_track_never_seen_offline_inverter(
    hass: HomeAssistant, mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """Inverters seen ONLY offline since startup must not enter the tracker.

    This guards against false `inverter_offline_long` issues for new hardware
    that has yet to come online for the first time.
    """
    from dataclasses import replace

    target_serial = mock_inverter_serials[0]
    offline_inverters = tuple(
        replace(inv, link_status=False) if inv.serial_number == target_serial else inv
        for inv in mock_plant_data.inverters
    )
    plant_with_offline = replace(mock_plant_data, inverters=offline_inverters)

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=plant_with_offline)

    meta = HoymilesMetadataCoordinator(hass, client, entry_id="test_entry")
    await meta.async_refresh()

    # The target inverter has never been seen online → must NOT appear in tracker.
    assert target_serial not in meta._last_seen_online


@pytest.mark.asyncio
async def test_real_data_coordinator_clears_dtu_unreachable_on_success(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """A successful poll always clears the `dtu_unreachable` Repair Issue.

    The deletion is unconditional (calling `async_delete_issue` on an absent
    issue is a documented no-op), so this test only asserts the call happens —
    not the side effect on a real registry.
    """
    from homeassistant.helpers import issue_registry as ir

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")
    # Pre-create the issue so we can verify the coordinator deletes it.
    ir.async_create_issue(
        hass,
        "hoymiles_dtupro",
        coord.issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="dtu_unreachable",
    )
    assert ir.async_get(hass).async_get_issue("hoymiles_dtupro", coord.issue_id) is not None

    await coord.async_refresh()

    assert ir.async_get(hass).async_get_issue("hoymiles_dtupro", coord.issue_id) is None


# ─── Custom thresholds (PR #4) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_real_data_coordinator_honours_custom_dtu_unreachable_threshold(
    hass: HomeAssistant,
) -> None:
    """When `dtu_unreachable_threshold` kwarg is given, _maybe_raise uses it.

    We assert by looking at the instance attribute rather than invoking the
    full Repair Issue lifecycle (which is already covered by test_repairs).
    """
    client = AsyncMock(spec=HoymilesAsyncClient)
    custom_threshold = timedelta(minutes=2)

    coord = HoymilesRealDataCoordinator(
        hass,
        client,
        entry_id="test_entry",
        host="192.0.2.1",
        dtu_unreachable_threshold=custom_threshold,
    )

    assert coord._dtu_unreachable_threshold == custom_threshold


@pytest.mark.asyncio
async def test_metadata_coordinator_honours_custom_inverter_offline_threshold(
    hass: HomeAssistant,
) -> None:
    """The inverter_offline_threshold kwarg drives `_evaluate_inverter_offline_issues`."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    custom_threshold = timedelta(hours=2)

    coord = HoymilesMetadataCoordinator(
        hass,
        client,
        entry_id="test_entry",
        inverter_offline_threshold=custom_threshold,
    )

    assert coord._inverter_offline_threshold == custom_threshold


@pytest.mark.asyncio
async def test_real_data_coordinator_default_threshold_preserved(
    hass: HomeAssistant,
) -> None:
    """Without an explicit kwarg, the coordinator falls back to the module default."""
    from custom_components.hoymiles_dtupro.const import ISSUE_DTU_UNREACHABLE_THRESHOLD

    client = AsyncMock(spec=HoymilesAsyncClient)

    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")

    assert coord._dtu_unreachable_threshold == ISSUE_DTU_UNREACHABLE_THRESHOLD


@pytest.mark.asyncio
async def test_metadata_coordinator_default_threshold_preserved(
    hass: HomeAssistant,
) -> None:
    """Without an explicit kwarg, the coordinator falls back to the module default."""
    from custom_components.hoymiles_dtupro.const import ISSUE_INVERTER_OFFLINE_THRESHOLD

    client = AsyncMock(spec=HoymilesAsyncClient)

    coord = HoymilesMetadataCoordinator(hass, client, entry_id="test_entry")

    assert coord._inverter_offline_threshold == ISSUE_INVERTER_OFFLINE_THRESHOLD


# --- PR #7 — TodayCache integration ------------------------------------------


@pytest.mark.asyncio
async def test_plant_today_production_clamped_is_none_before_first_poll(
    hass: HomeAssistant,
) -> None:
    """The exposed property is None until the coordinator has polled at least once."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")

    assert coord.plant_today_production_clamped is None


@pytest.mark.asyncio
async def test_plant_today_production_clamped_tracks_raw_on_first_poll(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """First successful poll seeds the cache with the raw plant sum."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)

    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")
    await coord.async_refresh()

    assert coord.plant_today_production_clamped == mock_plant_data.today_production


@pytest.mark.asyncio
async def test_plant_today_production_clamped_holds_through_rf_flap(
    hass: HomeAssistant,
    mock_plant_data: PlantData,
    mock_plant_data_one_offline: PlantData,
) -> None:
    """The canonical RF-flap scenario: high → drop → recover. Cache holds across drop.

    Without the cache, HA's recorder would credit the (high - drop) delta to
    `today` on the recovery cycle, inflating the cumulative by an order of
    magnitude over a day with 30-50 such flaps. The clamped value must remain
    monotone.
    """
    client = AsyncMock(spec=HoymilesAsyncClient)
    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")

    # Cycle 1 — all inverters online.
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    await coord.async_refresh()
    high = mock_plant_data.today_production
    assert high > 0  # sanity — fixture produces a non-trivial sum
    assert coord.plant_today_production_clamped == high

    # Cycle 2 — one inverter's RF link flaps (offline this poll only). Raw sum drops.
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data_one_offline)
    await coord.async_refresh()
    drop = mock_plant_data_one_offline.today_production
    assert drop < high  # sanity — fixture genuinely excludes the offline inverter
    # The cache must NOT decrease — published value stays at `high`.
    assert coord.plant_today_production_clamped == high

    # Cycle 3 — inverter rejoins, raw catches up to `high` again.
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    await coord.async_refresh()
    assert coord.plant_today_production_clamped == high


@pytest.mark.asyncio
async def test_today_cache_not_fed_on_failed_poll(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """A HoymilesError must NOT seed the cache (no data, no update)."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    client = AsyncMock(spec=HoymilesAsyncClient)
    coord = HoymilesRealDataCoordinator(hass, client, entry_id="test_entry", host="192.0.2.1")

    client.async_get_plant_data = AsyncMock(side_effect=HoymilesConnectionError("nope"))
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()

    assert coord.plant_today_production_clamped is None

    # First successful poll afterward establishes the baseline normally.
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    await coord.async_refresh()
    assert coord.plant_today_production_clamped == mock_plant_data.today_production
