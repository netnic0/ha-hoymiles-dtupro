"""Immutable data models for Hoymiles DTU-Pro readings.

Design choices (D4 in REFERENCES_HACS_MODERNES_2026.md):
  - `@dataclass(frozen=True, slots=True)` — no Pydantic dependency.
  - `__post_init__` performs invariant checks instead of runtime validators.
  - `Decimal` is intentionally NOT used; HA SensorEntity prefers `float`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, unique
from typing import Final

from .const import SERIES_PREFIX_HM, SERIES_PREFIX_MI


@unique
class InverterSeries(str, Enum):
    """Hoymiles inverter series, derived from the serial-number prefix.

    See MODBUS_PROTOCOL_DTUPRO.md §2 — prefix table.
    """

    MI = SERIES_PREFIX_MI
    """MI series (older, single-input). Serial starts with "10"."""

    HM = SERIES_PREFIX_HM
    """HM/HMS series (multi-input, e.g. HMS-1000-2T). Serial starts with "11"."""

    UNKNOWN = "??"
    """Unknown / future series."""

    @classmethod
    def from_serial(cls, serial: str) -> InverterSeries:
        """Identify the inverter series from its 12-char hex serial number."""
        prefix = serial[:2] if len(serial) >= 2 else ""
        if prefix == SERIES_PREFIX_MI:
            return cls.MI
        if prefix == SERIES_PREFIX_HM:
            return cls.HM
        return cls.UNKNOWN


# Sentinel used by some constructors to defer the timestamp to "now".
_DEFAULT_TS: Final[None] = None


@dataclass(frozen=True, slots=True)
class InverterReading:
    """Live data for one Hoymiles inverter at a given point in time.

    All numeric fields are already converted to engineering units
    (V, A, W, Wh, Hz, °C). Raw register values are NOT preserved here;
    use the decoder layer if you need the underlying integers.
    """

    serial_number: str
    """12-char uppercase hexadecimal serial (e.g. "1144000000A1")."""

    port_number: int
    """Inverter input port (1 or 2 for HMS-1000-2T)."""

    pv_voltage: float
    """PV-side DC voltage, in volts."""

    pv_current: float
    """PV-side DC current, in amperes."""

    grid_voltage: float
    """AC grid voltage, in volts."""

    grid_frequency: float
    """AC grid frequency, in hertz."""

    pv_power: float
    """Instantaneous PV-side DC power, in watts."""

    today_production: int
    """Energy produced today, in watt-hours."""

    total_production: int
    """Lifetime energy produced, in watt-hours (total_increasing)."""

    temperature: float
    """Inverter case temperature, in °C (can be negative)."""

    operating_status: int
    """Raw operating-status word (model-specific)."""

    alarm_code: int
    """Latest alarm code (0 == no alarm)."""

    alarm_count: int
    """Cumulative alarm count since power-on."""

    link_status: bool
    """True when the inverter is reachable via the DTU's RF link."""

    data_type: int
    """Raw `data_type` byte returned by the DTU (informational)."""

    def __post_init__(self) -> None:
        """Validate invariants. Raises ValueError if any field is out of range."""
        if len(self.serial_number) != 12:
            raise ValueError(
                f"serial_number must be 12 chars, got {len(self.serial_number)!r}"
            )
        if self.port_number < 0 or self.port_number > 255:
            raise ValueError(f"port_number out of range: {self.port_number}")
        if self.pv_voltage < 0 or self.pv_current < 0 or self.pv_power < 0:
            raise ValueError("PV-side V/A/W cannot be negative")
        if self.today_production < 0 or self.total_production < 0:
            raise ValueError("Production counters cannot be negative")

    @property
    def series(self) -> InverterSeries:
        """Inverter series derived from the serial-number prefix."""
        return InverterSeries.from_serial(self.serial_number)

    @property
    def has_alarm(self) -> bool:
        """True iff the inverter is reporting an active alarm."""
        return self.alarm_code != 0


@dataclass(frozen=True, slots=True)
class PlantData:
    """Aggregated plant-level snapshot built from a list of InverterReading.

    Aggregates ONLY readings whose `link_status` is True (mirrors ArekKubacki's
    behaviour and avoids stale values poisoning the totals).
    """

    dtu_serial: str
    inverters: tuple[InverterReading, ...] = field(default_factory=tuple)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.dtu_serial:
            raise ValueError("dtu_serial cannot be empty")

    @property
    def online_inverters(self) -> tuple[InverterReading, ...]:
        """Subset of inverters currently reachable through the DTU's RF link."""
        return tuple(inv for inv in self.inverters if inv.link_status)

    @property
    def pv_power(self) -> float:
        """Sum of instantaneous PV power for online inverters, in watts."""
        return sum(inv.pv_power for inv in self.online_inverters)

    @property
    def today_production(self) -> int:
        """Sum of today's production for online inverters, in watt-hours."""
        return sum(inv.today_production for inv in self.online_inverters)

    @property
    def total_production(self) -> int:
        """Sum of lifetime production for online inverters, in watt-hours."""
        return sum(inv.total_production for inv in self.online_inverters)

    @property
    def alarm_flag(self) -> bool:
        """True iff at least one online inverter is reporting an alarm."""
        return any(inv.has_alarm for inv in self.online_inverters)

    @property
    def inverter_count(self) -> int:
        """Total number of inverters detected (online + offline)."""
        return len(self.inverters)
