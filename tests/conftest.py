"""Pytest fixtures shared across the test suite."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from ha_hoymiles_dtupro.const import INVERTER_REGISTER_COUNT


def _bytes_to_registers(raw: bytes) -> list[int]:
    """Inverse of `_registers_to_bytes`: split a flat byte string into 16-bit registers."""
    if len(raw) % 2:
        raise ValueError("byte length must be even to be split into 16-bit registers")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, len(raw), 2)]


def make_modbus_response(payload: bytes) -> MagicMock:
    """Build a MagicMock matching pymodbus's ReadHoldingRegistersResponse contract."""
    response = MagicMock()
    response.isError = MagicMock(return_value=False)
    response.registers = _bytes_to_registers(payload)
    return response


def make_error_response() -> MagicMock:
    """Build a MagicMock representing a Modbus error response."""
    response = MagicMock()
    response.isError = MagicMock(return_value=True)
    return response


@pytest.fixture
def fake_pymodbus_client() -> Iterator[AsyncMock]:
    """An AsyncMock that mimics `pymodbus.client.AsyncModbusTcpClient`.

    The mock has:
      - `connect()` returning True
      - `read_holding_registers()` is an AsyncMock to be wired per-test
      - `close()` is a no-op MagicMock
    """
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.read_holding_registers = AsyncMock()
    client.close = MagicMock()
    yield client


@pytest.fixture
def inverter_register_count() -> int:
    """Expose INVERTER_REGISTER_COUNT to tests that hard-code expected counts."""
    return INVERTER_REGISTER_COUNT
