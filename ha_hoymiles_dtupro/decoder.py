"""Binary decoders for raw Modbus payloads.

All functions in this module are PURE (no I/O, no globals). They take raw
`bytes` from the Modbus layer and return either decoded model instances or
raise typed exceptions from `.exceptions`.

This isolation lets us unit-test the decoders against synthetic payloads
without any pymodbus / network dependency.
"""

from __future__ import annotations

import struct

from .const import (
    DTU_SERIAL_BYTES,
    INVERTER_FMT,
    INVERTER_PAYLOAD_BYTES,
    SCALE_GRID_FREQUENCY,
    SCALE_GRID_VOLTAGE,
    SCALE_PV_CURRENT_HM,
    SCALE_PV_CURRENT_MI,
    SCALE_PV_POWER,
    SCALE_PV_VOLTAGE,
    SCALE_TEMPERATURE,
    SERIES_PREFIX_MI,
)
from .exceptions import HoymilesDecodeError, HoymilesProtocolError
from .models import InverterReading


def decode_serial_number(raw: bytes) -> str:
    """Decode a 6-byte raw block into a 12-char uppercase hex serial.

    Raises HoymilesDecodeError if the buffer is shorter than expected.
    """
    if len(raw) < DTU_SERIAL_BYTES:
        raise HoymilesDecodeError(
            f"serial number requires {DTU_SERIAL_BYTES} bytes, got {len(raw)}"
        )
    return raw[:DTU_SERIAL_BYTES].hex().upper()


def _pv_current_scale(serial: str) -> float:
    """Pick the PV-current scale factor based on the inverter series."""
    if serial.startswith(SERIES_PREFIX_MI):
        return SCALE_PV_CURRENT_MI
    return SCALE_PV_CURRENT_HM


def decode_inverter_payload(raw: bytes) -> InverterReading:
    """Decode a 40-byte inverter payload into an InverterReading.

    Layout reference: ../../projets/photovoltaique-ve/MODBUS_PROTOCOL_DTUPRO.md §2.

    Raises:
        HoymilesDecodeError: if the buffer length is not exactly INVERTER_PAYLOAD_BYTES.
    """
    if len(raw) != INVERTER_PAYLOAD_BYTES:
        raise HoymilesDecodeError(
            f"inverter payload must be {INVERTER_PAYLOAD_BYTES} bytes, got {len(raw)}"
        )

    try:
        unpacked = struct.unpack(INVERTER_FMT, raw)
    except struct.error as exc:
        raise HoymilesDecodeError(f"struct.unpack failed: {exc}") from exc

    (
        data_type,
        serial_raw,
        port_number,
        pv_v_raw,
        pv_a_raw,
        grid_v_raw,
        grid_hz_raw,
        pv_p_raw,
        today_wh,
        total_wh,
        temp_raw,        # int16 signed
        operating_status,
        alarm_code,
        alarm_count,
        link_status_byte,
        # 7 bytes of reserved padding
        _r0, _r1, _r2, _r3, _r4, _r5, _r6,
    ) = unpacked

    serial = serial_raw.hex().upper()
    pv_current_scale = _pv_current_scale(serial)

    return InverterReading(
        serial_number=serial,
        port_number=port_number,
        pv_voltage=pv_v_raw * SCALE_PV_VOLTAGE,
        pv_current=pv_a_raw * pv_current_scale,
        grid_voltage=grid_v_raw * SCALE_GRID_VOLTAGE,
        grid_frequency=grid_hz_raw * SCALE_GRID_FREQUENCY,
        pv_power=pv_p_raw * SCALE_PV_POWER,
        today_production=int(today_wh),
        total_production=int(total_wh),
        temperature=temp_raw * SCALE_TEMPERATURE,
        operating_status=int(operating_status),
        alarm_code=int(alarm_code),
        alarm_count=int(alarm_count),
        link_status=bool(link_status_byte),
        data_type=int(data_type),
    )


def apply_data_size_fix(packet: bytes) -> bytes:
    """Patch the 1st byte of a Modbus response so it matches the actual payload length.

    Some Hoymiles DTU firmwares (notably V00.07.04 — see I3 in
    REVUE_CODE_AREKKUBACKI.md) return responses where the leading byte advertises
    an incorrect data size. This helper re-computes it from the trailing payload.

    This is a PURE function. The pymodbus integration hook (subclassing
    ReadHoldingRegistersResponse on async client) is intentionally NOT done here;
    it must be wired up only after live-DTU validation. See FI3 in plan review.
    """
    if not packet:
        raise HoymilesProtocolError("empty Modbus packet")

    fixed = bytearray(packet)
    actual = len(fixed) - 1  # everything except the size byte itself
    fixed[0] = actual & 0xFF
    return bytes(fixed)
