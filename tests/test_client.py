"""Tests for the async Modbus client orchestration logic.

The underlying pymodbus client is replaced by an AsyncMock so these tests
don't open any real socket.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ha_hoymiles_dtupro.client import HoymilesAsyncClient
from ha_hoymiles_dtupro.exceptions import (
    HoymilesConnectionError,
    HoymilesProtocolError,
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
