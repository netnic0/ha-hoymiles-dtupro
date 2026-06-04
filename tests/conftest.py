"""Pytest fixtures shared across the test suite.

Two layers of fixtures live here:

1. Pure-library helpers (`make_modbus_response`, `fake_pymodbus_client`, ...)
   used by the offline tests in test_client.py / test_decoder.py / test_models.py.

2. HA-native helpers (`mock_dtu_serial`, `mock_plant_data`, `mock_config_entry`)
   used by tests that import pytest-homeassistant-custom-component fixtures
   (`hass`, `enable_custom_integrations`).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from ha_hoymiles_dtupro.const import INVERTER_REGISTER_COUNT
from ha_hoymiles_dtupro.models import InverterReading, PlantData

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry


# ─── Pure-library helpers (unchanged from M0) ─────────────────────────────────


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
    """An AsyncMock that mimics `pymodbus.client.AsyncModbusTcpClient`."""
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.read_holding_registers = AsyncMock()
    client.close = MagicMock()
    yield client


@pytest.fixture
def inverter_register_count() -> int:
    """Expose INVERTER_REGISTER_COUNT to tests that hard-code expected counts."""
    return INVERTER_REGISTER_COUNT


# ─── HA-native fixtures ───────────────────────────────────────────────────────
#
# These rely on pytest-homeassistant-custom-component (PHCC) being installed.
# Tests that need them must also explicitly request the `enable_custom_integrations`
# PHCC fixture (per M1-D4) so the custom component loader picks up our manifest.


@pytest.fixture
def mock_dtu_serial() -> str:
    """Synthetic 12-char DTU serial for HA-native tests (mirrors fixture file)."""
    return "AABBCCDDEEFF"


@pytest.fixture
def mock_inverter_serials() -> list[str]:
    """Seven synthetic inverter serials matching the SEVEN_HMS_INVERTERS fixtures."""
    return [f"114400000{n:03X}" for n in range(0xA1, 0xA8)]


def _build_inverter_reading(serial: str, *, link: bool = True, alarm: int = 0) -> InverterReading:
    """Helper to build a syntactically-valid InverterReading for HA-native tests."""
    return InverterReading(
        serial_number=serial,
        port_number=1,
        pv_voltage=38.5,
        pv_current=8.21,
        grid_voltage=233.4,
        grid_frequency=50.02,
        pv_power=312.6,
        today_production=1850,
        total_production=985_000,
        temperature=41.3,
        operating_status=1,
        alarm_code=alarm,
        alarm_count=alarm,
        link_status=link,
        data_type=0,
    )


@pytest.fixture
def mock_plant_data(mock_dtu_serial: str, mock_inverter_serials: list[str]) -> PlantData:
    """A populated PlantData snapshot suitable for coordinator-state assertions."""
    return PlantData(
        dtu_serial=mock_dtu_serial,
        fetched_at=datetime(2026, 6, 4, 12, 0, 0, tzinfo=UTC),
        inverters=tuple(_build_inverter_reading(sn) for sn in mock_inverter_serials),
    )


@pytest.fixture
def mock_config_entry_data(mock_dtu_serial: str) -> dict[str, object]:
    """Default config entry payload for the Hoymiles DTU-Pro integration."""
    return {
        "host": "192.0.2.1",
        "port": 502,
        "unit_id": 1,
        "scan_interval_real_data": 30,
    }


@pytest.fixture
def mock_config_entry(mock_dtu_serial: str, mock_config_entry_data: dict) -> MockConfigEntry:
    """A MockConfigEntry pre-wired with the integration domain and unique_id.

    Tests that want to add it to hass should call:
        mock_config_entry.add_to_hass(hass)
    """
    # Lazy import: PHCC is in the dev dependency set but offline pure-lib tests
    # must remain importable without it.
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.const import DOMAIN

    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Hoymiles DTU-Pro ({mock_dtu_serial})",
        data=mock_config_entry_data,
        unique_id=mock_dtu_serial,
        version=1,
        minor_version=1,
    )
