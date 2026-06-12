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

from custom_components.hoymiles_dtupro.api.const import INVERTER_REGISTER_COUNT
from custom_components.hoymiles_dtupro.api.models import InverterReading, PlantData

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry


# --- Pure-library helpers (unchanged from M0) ---------------------------------


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


# --- HA-native fixtures -------------------------------------------------------
#
# These rely on pytest-homeassistant-custom-component (PHCC) being installed.
# The `enable_custom_integrations` PHCC fixture is autouse'd below so HA can
# resolve our domain via `async_get_integration("hoymiles_dtupro")` whenever a
# test triggers the config-/options-flow handler loader. Without it, calls
# like `hass.config_entries.options.async_init(entry_id)` raise UnknownHandler
# (CI bug surfaced by PR #5a — see GitHub run #47 of branch fix/pr5a-ci-hygiene).
#
# Pure-library tests that never request the `hass` fixture are unaffected: PHCC
# implements `enable_custom_integrations` as a yield-only fixture with no side
# effects when no Home Assistant instance is involved.


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    """Autouse wrapper around PHCC's `enable_custom_integrations`.

    We only activate the fixture when a test requests `hass` (or a fixture that
    transitively brings `hass` in) — this keeps pure-library tests free from
    the PHCC import cost and avoids spurious dependency on `hass` for offline
    tests.
    """
    if "hass" not in request.fixturenames:
        yield
        return

    enable = request.getfixturevalue("enable_custom_integrations")
    yield enable


@pytest.fixture
def mock_dtu_serial() -> str:
    """Synthetic 12-char DTU serial for HA-native tests (mirrors fixture file)."""
    return "AABBCCDDEEFF"


@pytest.fixture
def mock_inverter_serials() -> list[str]:
    """Seven synthetic inverter serials matching the SEVEN_HMS_INVERTERS fixtures."""
    return [f"114400000{n:03X}" for n in range(0xA1, 0xA8)]


def _build_inverter_reading(
    serial: str, port: int = 1, *, link: bool = True, alarm: int = 0
) -> InverterReading:
    """Build a syntactically-valid InverterReading for HA-native tests."""
    return InverterReading(
        serial_number=serial,
        port_number=port,
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
    """A populated PlantData snapshot with 2 ports per inverter (14 InverterReading total)."""
    readings = []
    for sn in mock_inverter_serials:
        readings.append(_build_inverter_reading(sn, port=1))
        readings.append(_build_inverter_reading(sn, port=2))
    return PlantData(
        dtu_serial=mock_dtu_serial,
        fetched_at=datetime(2026, 6, 4, 12, 0, 0, tzinfo=UTC),
        inverters=tuple(readings),
    )


@pytest.fixture
def mock_config_entry_data(mock_dtu_serial: str) -> dict[str, object]:
    """Default config entry payload for the Hoymiles DTU-Pro integration.

    From PR #4 (MINOR_VERSION=2), `scan_interval_real_data` lives in
    `entry.options`, not in `entry.data`. The `mock_config_entry` fixture
    below builds the entry with `options={}` (defaults will apply at runtime).
    """
    return {
        "host": "192.0.2.1",
        "port": 502,
        "unit_id": 1,
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
        options={},
        unique_id=mock_dtu_serial,
        version=1,
        minor_version=2,
    )


@pytest.fixture
def mock_config_entry_v1_legacy(mock_dtu_serial: str) -> MockConfigEntry:
    """A pre-PR-#4 (minor_version=1) config entry for migration testing.

    Mirrors the schema used before PR #4: `scan_interval_real_data` is in
    `data` rather than `options`. `async_migrate_entry` should move it.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.hoymiles_dtupro.const import DOMAIN

    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Hoymiles DTU-Pro ({mock_dtu_serial})",
        data={
            "host": "192.0.2.1",
            "port": 502,
            "unit_id": 1,
            "scan_interval_real_data": 30,
        },
        options={},
        unique_id=mock_dtu_serial,
        version=1,
        minor_version=1,
    )
