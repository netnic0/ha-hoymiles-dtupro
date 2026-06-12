"""Tests for the async Modbus client orchestration logic.

The underlying pymodbus client is replaced by an AsyncMock so these tests
don't open any real socket.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.hoymiles_dtupro.api.client import HoymilesAsyncClient
from custom_components.hoymiles_dtupro.api.exceptions import (
    HoymilesConnectionError,
    HoymilesProtocolError,
    HoymilesTimeoutError,
)
from tests.conftest import make_error_response, make_modbus_response
from tests.fixtures.inverter_samples import (
    SEVEN_HMS_INVERTERS,
    build_null_inverter_payload,
    dtu_serial_payload,
)


def _patch_pymodbus(fake_client) -> object:
    """Patch the lazy `pymodbus.client.AsyncModbusTcpClient` import."""
    return patch(
        "pymodbus.client.AsyncModbusTcpClient",
        return_value=fake_client,
    )


def test_constructor_rejects_empty_host() -> None:
    with pytest.raises(ValueError, match="host"):
        HoymilesAsyncClient(host="")


async def test_get_dtu_serial_returns_uppercase_hex(fake_pymodbus_client) -> None:
    fake_pymodbus_client.read_holding_registers.return_value = make_modbus_response(
        dtu_serial_payload()
    )
    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        serial = await client.async_get_dtu_serial()
    assert serial == "AABBCCDDEEFF"
    fake_pymodbus_client.connect.assert_awaited_once()
    fake_pymodbus_client.close.assert_called_once()


async def test_connect_failure_raises_connection_error(fake_pymodbus_client) -> None:
    fake_pymodbus_client.connect.return_value = False
    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        with pytest.raises(HoymilesConnectionError, match="returned False"):
            await client.async_get_dtu_serial()


async def test_modbus_error_response_raises_protocol_error(fake_pymodbus_client) -> None:
    fake_pymodbus_client.read_holding_registers.return_value = make_error_response()
    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        with pytest.raises(HoymilesProtocolError, match="Modbus error"):
            await client.async_get_dtu_serial()


async def test_get_inverters_iterates_until_null_sentinel(fake_pymodbus_client) -> None:
    """The scan stops at the first NULL_INVERTER and does not over-read."""
    payloads = [*SEVEN_HMS_INVERTERS, build_null_inverter_payload()]
    fake_pymodbus_client.read_holding_registers.side_effect = [
        make_modbus_response(p) for p in payloads
    ]
    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        inverters = await client.async_get_inverters()

    assert len(inverters) == 7
    serials = [inv.serial_number for inv in inverters]
    assert serials == [
        "1144000000A1",
        "1144000000A2",
        "1144000000A3",
        "1144000000A4",
        "1144000000A5",
        "1144000000A6",
        "1144000000A7",
    ]
    # 7 inverter slots + 1 null sentinel = 8 reads total.
    assert fake_pymodbus_client.read_holding_registers.await_count == 8


async def test_inverter_count_is_cached_for_subsequent_calls(fake_pymodbus_client) -> None:
    payloads_first = [*SEVEN_HMS_INVERTERS, build_null_inverter_payload()]
    payloads_second = [*SEVEN_HMS_INVERTERS, build_null_inverter_payload()]
    fake_pymodbus_client.read_holding_registers.side_effect = [
        make_modbus_response(p) for p in (*payloads_first, *payloads_second)
    ]
    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        await client.async_get_inverters()
        await client.async_get_inverters()

    # First scan: 8 reads. Second scan reuses the cached upper bound (7+1) → 8 reads.
    assert fake_pymodbus_client.read_holding_registers.await_count == 16


async def test_get_plant_data_returns_aggregated_snapshot(fake_pymodbus_client) -> None:
    """One call to async_get_plant_data should fetch DTU serial then inverters."""
    sequence = [
        make_modbus_response(dtu_serial_payload()),
        *(make_modbus_response(p) for p in SEVEN_HMS_INVERTERS),
        make_modbus_response(build_null_inverter_payload()),
    ]
    fake_pymodbus_client.read_holding_registers.side_effect = sequence

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        plant = await client.async_get_plant_data()

    assert plant.dtu_serial == "AABBCCDDEEFF"
    assert plant.inverter_count == 7
    assert plant.pv_power > 0  # all 7 inverters are online in our fixtures
    assert plant.alarm_flag is False


async def test_close_does_not_raise_even_if_underlying_close_fails(
    fake_pymodbus_client,
) -> None:
    """Best-effort close: errors during cleanup must not bubble up."""
    fake_pymodbus_client.read_holding_registers.return_value = make_modbus_response(
        dtu_serial_payload()
    )
    fake_pymodbus_client.close.side_effect = OSError("already closed")

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(host="192.0.2.10")
        # Should not raise even though close() blows up.
        serial = await client.async_get_dtu_serial()

    assert serial == "AABBCCDDEEFF"


# ─── Retry / backoff (PR #3) ───────────────────────────────────────────────


def test_constructor_rejects_invalid_retry_attempts() -> None:
    with pytest.raises(ValueError, match="retry_attempts"):
        HoymilesAsyncClient(host="192.0.2.10", retry_attempts=0)


def test_constructor_rejects_inverted_backoff() -> None:
    with pytest.raises(ValueError, match="backoff"):
        HoymilesAsyncClient(
            host="192.0.2.10",
            backoff_initial_s=2.0,
            backoff_max_s=1.0,
        )


def _plant_data_success_sequence():
    """Sequence of mocked Modbus responses for one successful plant fetch."""
    return [
        make_modbus_response(dtu_serial_payload()),
        *(make_modbus_response(p) for p in SEVEN_HMS_INVERTERS),
        make_modbus_response(build_null_inverter_payload()),
    ]


async def test_async_get_plant_data_retries_on_connection_error(
    fake_pymodbus_client,
) -> None:
    """A transient ConnectionError on the first attempt is retried successfully."""
    success = _plant_data_success_sequence()
    fake_pymodbus_client.read_holding_registers.side_effect = [
        ConnectionError("reset"),
        *success,
    ]

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            backoff_initial_s=0.0,  # speed up the test
            backoff_max_s=0.0,
        )
        plant = await client.async_get_plant_data()

    assert plant.dtu_serial == "AABBCCDDEEFF"
    assert plant.inverter_count == 7
    # 1 failed read + 9 successful reads on the retry attempt = 10 total.
    assert fake_pymodbus_client.read_holding_registers.await_count == 1 + len(success)
    # Two attempts → two TCP connections opened.
    assert fake_pymodbus_client.connect.await_count == 2


async def test_async_get_plant_data_retries_on_timeout(fake_pymodbus_client) -> None:
    """A TimeoutError on the first attempt is retried successfully."""
    success = _plant_data_success_sequence()
    fake_pymodbus_client.read_holding_registers.side_effect = [
        TimeoutError("slow DTU"),
        *success,
    ]

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            backoff_initial_s=0.0,
            backoff_max_s=0.0,
        )
        plant = await client.async_get_plant_data()

    assert plant.dtu_serial == "AABBCCDDEEFF"
    assert plant.inverter_count == 7
    assert fake_pymodbus_client.read_holding_registers.await_count == 1 + len(success)
    assert fake_pymodbus_client.connect.await_count == 2


async def test_async_get_plant_data_does_not_retry_protocol_error(
    fake_pymodbus_client,
) -> None:
    """Deterministic Modbus error responses must NOT be retried."""
    fake_pymodbus_client.read_holding_registers.return_value = make_error_response()

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            retry_attempts=3,
            backoff_initial_s=0.0,
            backoff_max_s=0.0,
        )
        with pytest.raises(HoymilesProtocolError, match="Modbus error"):
            await client.async_get_plant_data()

    # No retry: a single read call, a single connect call.
    assert fake_pymodbus_client.read_holding_registers.await_count == 1
    assert fake_pymodbus_client.connect.await_count == 1


async def test_async_get_plant_data_gives_up_after_max_attempts(
    fake_pymodbus_client,
) -> None:
    """After `retry_attempts` consecutive failures, the last error propagates."""
    fake_pymodbus_client.read_holding_registers.side_effect = [
        ConnectionError("reset 1"),
        ConnectionError("reset 2"),
        ConnectionError("reset 3"),
    ]

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            retry_attempts=3,
            backoff_initial_s=0.0,
            backoff_max_s=0.0,
        )
        with pytest.raises(HoymilesConnectionError):
            await client.async_get_plant_data()

    # Critical assertion (validates Option A vs B):
    # a fresh TCP socket is opened on every attempt, not reused.
    assert fake_pymodbus_client.connect.await_count == 3
    assert fake_pymodbus_client.read_holding_registers.await_count == 3


async def test_async_get_plant_data_propagates_timeout_after_exhaustion(
    fake_pymodbus_client,
) -> None:
    """Exhaustion of retries on a timeout chain raises HoymilesTimeoutError."""
    fake_pymodbus_client.read_holding_registers.side_effect = [
        TimeoutError("t1"),
        TimeoutError("t2"),
    ]

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            retry_attempts=2,
            backoff_initial_s=0.0,
            backoff_max_s=0.0,
        )
        with pytest.raises(HoymilesTimeoutError):
            await client.async_get_plant_data()

    assert fake_pymodbus_client.connect.await_count == 2


async def test_async_get_plant_data_retries_on_open_failure(
    fake_pymodbus_client,
) -> None:
    """A failure during _open() (connect raising OSError) triggers retry.

    Covers a code path that the read_holding_registers retry tests do NOT
    exercise: the failure originates BEFORE any register read, in the
    `client.connect()` call inside `_open`.
    """
    success = _plant_data_success_sequence()
    fake_pymodbus_client.connect.side_effect = [OSError("no route"), True]
    fake_pymodbus_client.read_holding_registers.side_effect = success

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            backoff_initial_s=0.0,
            backoff_max_s=0.0,
        )
        plant = await client.async_get_plant_data()

    assert plant.dtu_serial == "AABBCCDDEEFF"
    # 2 attempts: first connect raised, second succeeded.
    assert fake_pymodbus_client.connect.await_count == 2


async def test_async_get_plant_data_preserves_exception_cause(
    fake_pymodbus_client,
) -> None:
    """After all retries exhaust, the raised HoymilesError keeps the original
    OSError chained via __cause__ — the underlying network error is not lost."""
    fake_pymodbus_client.read_holding_registers.side_effect = [
        ConnectionError("first"),
        ConnectionError("second"),
    ]

    with _patch_pymodbus(fake_pymodbus_client):
        client = HoymilesAsyncClient(
            host="192.0.2.10",
            retry_attempts=2,
            backoff_initial_s=0.0,
            backoff_max_s=0.0,
        )
        with pytest.raises(HoymilesConnectionError) as exc_info:
            await client.async_get_plant_data()

    # The HoymilesConnectionError wraps the original OSError-family exception
    # via `raise ... from err` in `_read_holding_registers`.
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ConnectionError)
