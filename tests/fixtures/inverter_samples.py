"""Synthetic binary fixtures for inverter payload tests.

Builds 40-byte payloads in pure Python so tests don't depend on a real DTU.
The serial numbers are FAKE (no real hardware exposed in this repo).
"""

from __future__ import annotations

import struct
from typing import Final

from ha_hoymiles_dtupro.const import INVERTER_FMT, NULL_INVERTER_SERIAL


def build_inverter_payload(  # noqa: PLR0913 -- builder helper
    *,
    serial_hex: str = "1144000000A1",
    port_number: int = 1,
    pv_voltage_v: float = 38.5,
    pv_current_a: float = 8.21,
    grid_voltage_v: float = 233.4,
    grid_frequency_hz: float = 50.02,
    pv_power_w: float = 312.6,
    today_wh: int = 1850,
    total_wh: int = 985_000,
    temperature_c: float = 41.3,
    operating_status: int = 1,
    alarm_code: int = 0,
    alarm_count: int = 0,
    link_status: int = 1,
    data_type: int = 0,
) -> bytes:
    """Pack realistic field values into a 40-byte payload matching INVERTER_FMT."""
    if len(serial_hex) != 12:
        raise ValueError("serial_hex must be 12 hex characters")
    serial_bytes = bytes.fromhex(serial_hex)

    return struct.pack(
        INVERTER_FMT,
        data_type,
        serial_bytes,
        port_number,
        round(pv_voltage_v / 0.1),
        round(pv_current_a / 0.01),
        round(grid_voltage_v / 0.1),
        round(grid_frequency_hz / 0.01),
        round(pv_power_w / 0.1),
        today_wh,
        total_wh,
        round(temperature_c / 0.1),
        operating_status,
        alarm_code,
        alarm_count,
        link_status,
        0, 0, 0, 0, 0, 0, 0,  # 7 reserved bytes
    )


def build_null_inverter_payload() -> bytes:
    """Build the sentinel payload that terminates the inverter scan loop."""
    return build_inverter_payload(serial_hex=NULL_INVERTER_SERIAL, link_status=0)


# Pre-built payload for a synthetic 7-inverter HMS-1000-2T plant.
# Serial numbers are FAKE: the "1144" prefix preserves the HM-series detection
# (cf. InverterSeries.from_serial), the rest is intentionally non-real.
SEVEN_HMS_INVERTERS: Final[tuple[bytes, ...]] = (
    build_inverter_payload(serial_hex="1144000000A1", port_number=1, pv_power_w=310.0),
    build_inverter_payload(serial_hex="1144000000A2", port_number=1, pv_power_w=308.5),
    build_inverter_payload(serial_hex="1144000000A3", port_number=1, pv_power_w=315.2),
    build_inverter_payload(serial_hex="1144000000A4", port_number=1, pv_power_w=311.0),
    build_inverter_payload(serial_hex="1144000000A5", port_number=1, pv_power_w=128.5),
    build_inverter_payload(serial_hex="1144000000A6", port_number=1, pv_power_w=129.0),
    build_inverter_payload(serial_hex="1144000000A7", port_number=1, pv_power_w=127.8),
)


def dtu_serial_payload() -> bytes:
    """Six-byte synthetic DTU serial number used in fixtures (AABBCCDDEEFF)."""
    return bytes.fromhex("AABBCCDDEEFF")
