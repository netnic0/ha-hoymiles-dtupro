"""Async Modbus TCP client for Hoymiles DTU-Pro.

Wraps `pymodbus.client.AsyncModbusTcpClient` to:
  - manage connection lifecycle,
  - iterate inverter slots until NULL_INVERTER_SERIAL,
  - decode responses via the pure functions in `decoder`,
  - translate pymodbus errors into the typed `HoymilesError` hierarchy.

The decoders are kept separate (see `decoder.py`) so they can be tested
without any pymodbus mock. Here we only test the orchestration logic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Final

from .const import (
    DEFAULT_BACKOFF_INITIAL_S,
    DEFAULT_BACKOFF_MAX_S,
    DEFAULT_PORT,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT_S,
    DEFAULT_UNIT_ID,
    DTU_SERIAL_REGISTER_COUNT,
    INVERTER_PAYLOAD_BYTES,
    INVERTER_REGISTER_COUNT,
    INVERTER_REGISTER_STRIDE,
    MAX_INVERTER_SCAN,
    MODBUS_REGISTER_DTU_SERIAL,
    MODBUS_REGISTER_INVERTER_BASE,
    NULL_INVERTER_SERIAL,
)
from .decoder import apply_data_size_fix, decode_inverter_payload, decode_serial_number
from .exceptions import (
    HoymilesConnectionError,
    HoymilesError,
    HoymilesProtocolError,
    HoymilesTimeoutError,
)
from .models import InverterReading, PlantData

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Awaitable, Callable

    from pymodbus.client import AsyncModbusTcpClient

_LOGGER: Final = logging.getLogger(__name__)


def _registers_to_bytes(registers: list[int]) -> bytes:
    """Serialise a list of 16-bit registers (big-endian) to a flat byte string."""
    return b"".join(reg.to_bytes(2, "big") for reg in registers)


class HoymilesAsyncClient:
    """Asynchronous Modbus TCP client for a Hoymiles DTU-Pro.

    The client is intentionally stateless across calls (each `async_get_*`
    opens, queries, and closes the underlying TCP connection). This mirrors
    ArekKubacki's design and keeps the DTU happy with its single-connection
    Modbus stack.

    For multi-coordinator setups (FC3 in plan review), a SINGLE instance of
    this class must be shared across coordinators — never instantiate twice
    against the same DTU.
    """

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        unit_id: int = DEFAULT_UNIT_ID,
        timeout: float = DEFAULT_TIMEOUT_S,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        backoff_initial_s: float = DEFAULT_BACKOFF_INITIAL_S,
        backoff_max_s: float = DEFAULT_BACKOFF_MAX_S,
    ) -> None:
        if not host:
            raise ValueError("host cannot be empty")
        if retry_attempts < 1:
            raise ValueError("retry_attempts must be >= 1")
        if backoff_initial_s < 0 or backoff_max_s < backoff_initial_s:
            raise ValueError("backoff parameters invalid: require 0 <= initial <= max")
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._backoff_initial_s = backoff_initial_s
        self._backoff_max_s = backoff_max_s
        self._cached_inverter_count: int | None = None
        self._lock = asyncio.Lock()
        """Guards concurrent fetches against the same DTU (see FC3)."""

    # ─── Public API ────────────────────────────────────────────────────────
    async def async_get_dtu_serial(self) -> str:
        """Return the DTU serial number as a 12-char uppercase hex string."""
        # The lock is intentionally held for the entire retry sequence.
        # Releasing between attempts would let a second coordinator start a
        # fetch on the same DTU while we are already backing off, compounding
        # the load on a device that is already struggling. Worst-case hold
        # time with default settings: ~16.5 s.
        async with self._lock:
            return await self._fetch_with_retry(self._fetch_dtu_serial_once)

    async def async_get_inverters(self) -> list[InverterReading]:
        """Return the list of all live inverter readings."""
        # Lock held for the full retry duration — see async_get_dtu_serial.
        async with self._lock:
            return await self._fetch_with_retry(self._fetch_inverters_once)

    async def async_get_plant_data(self) -> PlantData:
        """Convenience: serial + inverters in one batch (single connection)."""
        # Lock held for the full retry duration — see async_get_dtu_serial.
        async with self._lock:
            return await self._fetch_with_retry(self._fetch_plant_once)

    # ─── Transactional fetch helpers (one open → reads → close cycle each) ─
    async def _fetch_dtu_serial_once(self) -> str:
        """One transactional attempt at reading the DTU serial number."""
        client = await self._open()
        try:
            raw = await self._read_holding_registers(
                client,
                address=MODBUS_REGISTER_DTU_SERIAL,
                count=DTU_SERIAL_REGISTER_COUNT,
            )
            return decode_serial_number(raw)
        finally:
            self._close(client)

    async def _fetch_inverters_once(self) -> list[InverterReading]:
        """One transactional attempt at reading all inverter slots."""
        client = await self._open()
        try:
            return await self._read_all_inverters(client)
        finally:
            self._close(client)

    async def _fetch_plant_once(self) -> PlantData:
        """One transactional attempt at reading serial + inverters."""
        client = await self._open()
        try:
            serial_raw = await self._read_holding_registers(
                client,
                address=MODBUS_REGISTER_DTU_SERIAL,
                count=DTU_SERIAL_REGISTER_COUNT,
            )
            dtu_serial = decode_serial_number(serial_raw)
            inverters = await self._read_all_inverters(client)
            return PlantData(dtu_serial=dtu_serial, inverters=tuple(inverters))
        finally:
            self._close(client)

    # ─── Retry orchestrator ───────────────────────────────────────────────
    async def _fetch_with_retry[T](self, fetch_fn: Callable[[], Awaitable[T]]) -> T:
        """Run `fetch_fn` with up to `_retry_attempts` attempts and backoff.

        Retries only on transient errors (connection lost, timeout). Deterministic
        protocol errors (`HoymilesProtocolError`) propagate immediately — a
        malformed frame at a specific slot will keep being malformed.

        Each attempt opens a fresh TCP socket via the wrapped `fetch_fn`.
        """
        backoff = self._backoff_initial_s
        last_err: HoymilesError | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                return await fetch_fn()
            except (HoymilesConnectionError, HoymilesTimeoutError) as err:
                last_err = err
                _LOGGER.debug(
                    "Hoymiles fetch attempt %d/%d failed: %s",
                    attempt,
                    self._retry_attempts,
                    err,
                )
                if attempt == self._retry_attempts:
                    break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._backoff_max_s)
            # HoymilesProtocolError is *not* caught here — fail-fast on
            # deterministic frames; retrying wastes wall-clock time.
        # `last_err` is always set: the loop runs >= 1 time and every except
        # branch assigns it before `break`. mypy cannot prove this across loop
        # iterations, so `last_err` is typed `Exception | None`. With the
        # PR #5b config (`disable_error_code = ["misc"]`) the previously needed
        # `# type: ignore[misc]` is now redundant.
        raise last_err  # noqa: RUF100

    # ─── Internal helpers ─────────────────────────────────────────────────
    async def _open(self) -> AsyncModbusTcpClient:
        """Open the underlying pymodbus async client. Lazy import to avoid
        hard-loading pymodbus at module import time (helps test isolation)."""
        from pymodbus.client import AsyncModbusTcpClient

        client = AsyncModbusTcpClient(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )
        try:
            connected = await client.connect()
        except (TimeoutError, OSError) as err:
            raise HoymilesConnectionError(
                f"cannot connect to {self._host}:{self._port}: {err}"
            ) from err

        if not connected:
            raise HoymilesConnectionError(f"connect() returned False for {self._host}:{self._port}")
        _LOGGER.debug("Connected to Hoymiles DTU at %s:%s", self._host, self._port)
        return client

    @staticmethod
    def _close(client: AsyncModbusTcpClient) -> None:
        """Best-effort close; does not raise."""
        try:
            client.close()
        except Exception:
            _LOGGER.debug("client.close() raised; ignoring", exc_info=True)

    async def _read_holding_registers(
        self,
        client: AsyncModbusTcpClient,
        address: int,
        count: int,
    ) -> bytes:
        """Read `count` 16-bit holding registers and return them as raw bytes."""
        try:
            response = await client.read_holding_registers(
                address=address,
                count=count,
                device_id=self._unit_id,
            )
        except TimeoutError as err:
            raise HoymilesTimeoutError(
                f"timeout reading register 0x{address:04X} (count={count})"
            ) from err
        except (OSError, ConnectionError) as err:
            raise HoymilesConnectionError(
                f"connection lost reading register 0x{address:04X}"
            ) from err

        if response.isError():
            raise HoymilesProtocolError(f"Modbus error response at 0x{address:04X}: {response}")

        registers: list[int] = list(response.registers)
        return _registers_to_bytes(registers)

    async def _read_all_inverters(self, client: AsyncModbusTcpClient) -> list[InverterReading]:
        """Iterate inverter slots until NULL_INVERTER_SERIAL or MAX_INVERTER_SCAN.

        Pre-existing behaviour: ``_cached_inverter_count`` is not rolled back on
        partial failure mid-loop. The retry layer slightly amplifies this
        exposure (a transient mid-scan failure followed by a successful retry
        could theoretically mismatch the cache for one cycle), but the cache is
        self-correcting on the next successful full scan. PR #5 may revisit.
        """
        inverters: list[InverterReading] = []
        scan_upper = self._cached_inverter_count or MAX_INVERTER_SCAN

        for index in range(scan_upper + 1):
            address = MODBUS_REGISTER_INVERTER_BASE + index * INVERTER_REGISTER_STRIDE
            raw = await self._read_holding_registers(
                client, address=address, count=INVERTER_REGISTER_COUNT
            )
            if len(raw) != INVERTER_PAYLOAD_BYTES:
                raise HoymilesProtocolError(f"unexpected payload size {len(raw)} at slot {index}")
            raw = apply_data_size_fix(raw)
            reading = decode_inverter_payload(raw)
            if reading.serial_number == NULL_INVERTER_SERIAL:
                _LOGGER.debug("NULL_INVERTER reached at slot %d, stopping", index)
                # Cache the inverter count so we don't scan past it next time.
                self._cached_inverter_count = max(index + 1, 1)
                break
            inverters.append(reading)
        else:
            _LOGGER.warning(
                "Inverter scan reached MAX_INVERTER_SCAN=%d without NULL_INVERTER",
                scan_upper,
            )

        return inverters
