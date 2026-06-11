"""HA-native tests for the Hoymiles DTU-Pro Repair Issues (PR #2).

Covers the lifecycle of:
  * `dtu_unreachable_<entry_id>`     — fired when the DTU has been silent past
    `ISSUE_DTU_UNREACHABLE_THRESHOLD`; cleared on the next successful poll.
  * `inverter_offline_<serial>_<entry_id>` — fired per inverter once
    `link_status=False` has held continuously for more than
    `ISSUE_INVERTER_OFFLINE_THRESHOLD`. Guarded against false positives for
    inverters never seen online since startup.

The fast (sub-second) tests below stub the timers manually rather than waiting
for real wall-clock thresholds. They drive the coordinator directly and assert
on the `homeassistant.helpers.issue_registry` state.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from custom_components.hoymiles_dtupro.api.client import HoymilesAsyncClient
from custom_components.hoymiles_dtupro.api.exceptions import HoymilesConnectionError
from custom_components.hoymiles_dtupro.const import (
    DOMAIN,
    ISSUE_DTU_UNREACHABLE_THRESHOLD,
    ISSUE_ID_DTU_UNREACHABLE,
    ISSUE_ID_INVERTER_OFFLINE,
    ISSUE_INVERTER_OFFLINE_THRESHOLD,
)
from custom_components.hoymiles_dtupro.coordinator import (
    HoymilesMetadataCoordinator,
    HoymilesRealDataCoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.hoymiles_dtupro.api.models import PlantData


_ENTRY_ID = "test_entry"
_HOST = "192.0.2.1"


def _dtu_issue_id(entry_id: str = _ENTRY_ID) -> str:
    return f"{ISSUE_ID_DTU_UNREACHABLE}_{entry_id}"


def _inv_issue_id(serial: str, entry_id: str = _ENTRY_ID) -> str:
    return f"{ISSUE_ID_INVERTER_OFFLINE}_{serial}_{entry_id}"


# ─────────────────────────────────────────────────────────────────────────────
# DTU unreachable
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dtu_unreachable_not_raised_before_threshold(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """A single failed poll must NOT raise the dtu_unreachable issue.

    The grace window is `ISSUE_DTU_UNREACHABLE_THRESHOLD` measured from the
    last successful update — this test ensures we do not flap on transient
    one-shot errors.
    """
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    coord = HoymilesRealDataCoordinator(hass, client, entry_id=_ENTRY_ID, host=_HOST)

    # First poll succeeds → records last_update_success_time.
    await coord.async_refresh()
    assert coord.last_update_success is True

    # Second poll fails. Elapsed since last success ≪ threshold → no issue.
    client.async_get_plant_data = AsyncMock(side_effect=HoymilesConnectionError("nope"))
    await coord.async_refresh()
    assert coord.last_update_success is False
    assert ir.async_get(hass).async_get_issue(DOMAIN, _dtu_issue_id()) is None


@pytest.mark.asyncio
async def test_dtu_unreachable_raised_after_threshold(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """Once `last_update_success_time` is older than the threshold, fire the issue."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    coord = HoymilesRealDataCoordinator(hass, client, entry_id=_ENTRY_ID, host=_HOST)

    await coord.async_refresh()
    # Backdate the last success to past the 5-minute threshold.
    coord.last_update_success_time = dt_util.utcnow() - (
        ISSUE_DTU_UNREACHABLE_THRESHOLD + ISSUE_DTU_UNREACHABLE_THRESHOLD
    )

    client.async_get_plant_data = AsyncMock(side_effect=HoymilesConnectionError("nope"))
    await coord.async_refresh()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, _dtu_issue_id())
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.ERROR
    assert issue.translation_key == ISSUE_ID_DTU_UNREACHABLE
    assert issue.translation_placeholders == {"host": _HOST}


@pytest.mark.asyncio
async def test_dtu_unreachable_cleared_on_recovery(
    hass: HomeAssistant, mock_plant_data: PlantData
) -> None:
    """Once a poll succeeds again, the dtu_unreachable issue is removed."""
    client = AsyncMock(spec=HoymilesAsyncClient)
    coord = HoymilesRealDataCoordinator(hass, client, entry_id=_ENTRY_ID, host=_HOST)

    # Manually create the issue (simulating a previously-fired alert).
    ir.async_create_issue(
        hass,
        DOMAIN,
        _dtu_issue_id(),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_ID_DTU_UNREACHABLE,
        translation_placeholders={"host": _HOST},
    )
    assert ir.async_get(hass).async_get_issue(DOMAIN, _dtu_issue_id()) is not None

    # A successful poll must clear the issue.
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    await coord.async_refresh()

    assert ir.async_get(hass).async_get_issue(DOMAIN, _dtu_issue_id()) is None


# ─────────────────────────────────────────────────────────────────────────────
# Inverter offline (per serial, with never-seen-online guard)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inverter_offline_not_raised_before_threshold(
    hass: HomeAssistant, mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """An inverter that just went offline (within tolerance) does not raise the issue."""
    target_serial = mock_inverter_serials[0]
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    coord = HoymilesMetadataCoordinator(hass, client, entry_id=_ENTRY_ID)

    # First poll: everyone online → recorded in tracker.
    await coord.async_refresh()
    assert target_serial in coord._last_seen_online

    # Second poll: target is now offline, but the tracker timestamp is recent.
    offline_inv = tuple(
        replace(inv, link_status=False) if inv.serial_number == target_serial else inv
        for inv in mock_plant_data.inverters
    )
    plant_offline = replace(mock_plant_data, inverters=offline_inv)
    client.async_get_plant_data = AsyncMock(return_value=plant_offline)
    await coord.async_refresh()

    assert ir.async_get(hass).async_get_issue(DOMAIN, _inv_issue_id(target_serial)) is None


@pytest.mark.asyncio
async def test_inverter_offline_raised_after_threshold(
    hass: HomeAssistant, mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """Once the tracked sighting is older than 6h and the inverter is offline, raise the issue."""
    target_serial = mock_inverter_serials[0]
    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    coord = HoymilesMetadataCoordinator(hass, client, entry_id=_ENTRY_ID)

    # First poll: everyone online → recorded in tracker.
    await coord.async_refresh()

    # Backdate the tracked sighting beyond the offline threshold.
    coord._last_seen_online[target_serial] = dt_util.utcnow() - (
        ISSUE_INVERTER_OFFLINE_THRESHOLD + ISSUE_INVERTER_OFFLINE_THRESHOLD
    )

    offline_inv = tuple(
        replace(inv, link_status=False) if inv.serial_number == target_serial else inv
        for inv in mock_plant_data.inverters
    )
    plant_offline = replace(mock_plant_data, inverters=offline_inv)
    client.async_get_plant_data = AsyncMock(return_value=plant_offline)
    await coord.async_refresh()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, _inv_issue_id(target_serial))
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.translation_key == ISSUE_ID_INVERTER_OFFLINE
    assert issue.translation_placeholders == {"serial": target_serial}


@pytest.mark.asyncio
async def test_inverter_offline_cleared_on_recovery(
    hass: HomeAssistant, mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """Once the inverter comes back online, its `inverter_offline_long` issue is cleared."""
    target_serial = mock_inverter_serials[0]

    # Pre-create the issue (simulating a previously-fired alert).
    ir.async_create_issue(
        hass,
        DOMAIN,
        _inv_issue_id(target_serial),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_ID_INVERTER_OFFLINE,
        translation_placeholders={"serial": target_serial},
    )

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=mock_plant_data)
    coord = HoymilesMetadataCoordinator(hass, client, entry_id=_ENTRY_ID)
    await coord.async_refresh()

    assert ir.async_get(hass).async_get_issue(DOMAIN, _inv_issue_id(target_serial)) is None


@pytest.mark.asyncio
async def test_inverter_offline_never_seen_online_does_not_fire(
    hass: HomeAssistant, mock_plant_data: PlantData, mock_inverter_serials: list[str]
) -> None:
    """An inverter that is offline since the very first poll must not raise.

    This guards against false positives for newly added hardware that has yet
    to come online for the first time since this integration load.
    """
    target_serial = mock_inverter_serials[0]
    offline_inv = tuple(
        replace(inv, link_status=False) if inv.serial_number == target_serial else inv
        for inv in mock_plant_data.inverters
    )
    plant_offline = replace(mock_plant_data, inverters=offline_inv)

    client = AsyncMock(spec=HoymilesAsyncClient)
    client.async_get_plant_data = AsyncMock(return_value=plant_offline)
    coord = HoymilesMetadataCoordinator(hass, client, entry_id=_ENTRY_ID)
    await coord.async_refresh()

    # Even a thousand polls later, with no observation of link_status=True,
    # the issue must NOT be raised: the timer never started.
    for _ in range(3):
        await coord.async_refresh()

    assert ir.async_get(hass).async_get_issue(DOMAIN, _inv_issue_id(target_serial)) is None
    assert target_serial not in coord._last_seen_online
