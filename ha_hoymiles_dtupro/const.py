"""Constants for the Hoymiles DTU-Pro Modbus client.

Source of truth: ../../projets/photovoltaique-ve/MODBUS_PROTOCOL_DTUPRO.md (sections 1-2).

Reverse-engineered from ArekKubacki/Hoymiles-Plant-DTU-Pro (MIT).
Validated against `datatypes.py` of that repo (cloned in `_research/arekkubacki/`).
"""

from __future__ import annotations

import struct
from typing import Final

# ─── Modbus register map (DTU type 0 — standard Hoymiles HMS / HM series) ──────
MODBUS_REGISTER_INVERTER_BASE: Final[int] = 0x1000
"""First inverter register address. Inverter `i` lives at BASE + i * 40."""

INVERTER_REGISTER_STRIDE: Final[int] = 40
"""Register offset between two consecutive inverters (DTU type 0)."""

INVERTER_REGISTER_COUNT: Final[int] = 20
"""Number of registers (16-bit each) to read per inverter = 40 bytes raw."""

INVERTER_PAYLOAD_BYTES: Final[int] = 40
"""Decoded payload size per inverter, in bytes (after Modbus header strip)."""

MODBUS_REGISTER_DTU_SERIAL: Final[int] = 0x2000
"""DTU serial-number register block start."""

DTU_SERIAL_REGISTER_COUNT: Final[int] = 3
"""Number of registers for the DTU serial number (= 6 bytes)."""

DTU_SERIAL_BYTES: Final[int] = 6
"""DTU serial number length in bytes (decoded as 12-char uppercase hex)."""

# ─── Sentinel values ──────────────────────────────────────────────────────────
NULL_INVERTER_SERIAL: Final[str] = "000000000000"
"""Serial number returned by an unmapped inverter slot (loop terminator)."""

MAX_INVERTER_SCAN: Final[int] = 100
"""Hard upper bound on the inverter-scan loop (mirrors ArekKubacki). The actual
loop stops earlier when NULL_INVERTER_SERIAL is encountered."""

# ─── Default Modbus connection settings ───────────────────────────────────────
DEFAULT_PORT: Final[int] = 502
DEFAULT_UNIT_ID: Final[int] = 1
DEFAULT_TIMEOUT_S: Final[float] = 5.0
DEFAULT_RETRIES: Final[int] = 3
"""Reduced from ArekKubacki's 5 to lower DTU stress."""

# ─── DTU type discriminator ───────────────────────────────────────────────────
DTU_TYPE_STANDARD: Final[int] = 0
"""Standard DTU-Pro Hoymiles (40-byte inverter payload). Tested in production."""

DTU_TYPE_LEGACY: Final[int] = 1
"""Variant with i*20 stride. Mentioned upstream but not confirmed."""

DTU_TYPE_OPENDTU: Final[int] = 2
"""OpenDTU 80-byte payload. Out of scope for this PoC."""

# ─── Inverter binary layout (40 bytes, big-endian) ────────────────────────────
# See MODBUS_PROTOCOL_DTUPRO.md §2 for the byte-by-byte breakdown.
#
# Layout:
#   B    data_type             (1 byte,  uint8)
#   6s   serial_number         (6 bytes, raw — decoded to 12-char hex)
#   B    port_number           (1 byte,  uint8)
#   H    pv_voltage_raw        (2 bytes, uint16, scale 0.1 V)
#   H    pv_current_raw        (2 bytes, uint16, scale 0.01 A)
#   H    grid_voltage_raw      (2 bytes, uint16, scale 0.1 V)
#   H    grid_frequency_raw    (2 bytes, uint16, scale 0.01 Hz)
#   H    pv_power_raw          (2 bytes, uint16, scale 0.1 W)
#   H    today_production      (2 bytes, uint16, Wh)
#   I    total_production      (4 bytes, uint32, Wh)
#   h    temperature_raw       (2 bytes, INT16 signed, scale 0.1 °C)
#   H    operating_status      (2 bytes, uint16)
#   H    alarm_code            (2 bytes, uint16)
#   H    alarm_count           (2 bytes, uint16)
#   B    link_status           (1 byte,  uint8)
#   7B   reserved              (7 bytes, padding — ignored)
INVERTER_FMT: Final[str] = ">B6sBHHHHHHIhHHHB7B"

# Compile-time guard: catch any future edit that breaks the 40-byte contract.
assert struct.calcsize(INVERTER_FMT) == INVERTER_PAYLOAD_BYTES, (
    f"INVERTER_FMT must encode exactly {INVERTER_PAYLOAD_BYTES} bytes, "
    f"got {struct.calcsize(INVERTER_FMT)}"
)

# ─── Scale factors (decode integer registers into engineering units) ──────────
SCALE_PV_VOLTAGE: Final[float] = 0.1       # V
SCALE_PV_CURRENT_HM: Final[float] = 0.01   # A (HM/HMS series, SN starts with "11")
SCALE_PV_CURRENT_MI: Final[float] = 0.01   # A (MI series, SN starts with "10")
SCALE_GRID_VOLTAGE: Final[float] = 0.1     # V
SCALE_GRID_FREQUENCY: Final[float] = 0.01  # Hz
SCALE_PV_POWER: Final[float] = 0.1         # W
SCALE_TEMPERATURE: Final[float] = 0.1      # °C (signed)

# ─── Inverter-series prefix discriminator (first 2 chars of serial) ───────────
SERIES_PREFIX_MI: Final[str] = "10"
SERIES_PREFIX_HM: Final[str] = "11"
"""HM and HMS share prefix "11" — see MODBUS_PROTOCOL_DTUPRO.md §2."""
