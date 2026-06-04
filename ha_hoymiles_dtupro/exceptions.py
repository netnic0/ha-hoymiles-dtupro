"""Exception hierarchy for the Hoymiles DTU-Pro client.

All exceptions raised by this library inherit from `HoymilesError`.
This lets HA's `DataUpdateCoordinator` catch a single base class and decide
whether to raise `UpdateFailed` (transient) or `ConfigEntryAuthFailed` (fatal).
"""

from __future__ import annotations


class HoymilesError(Exception):
    """Base class for all Hoymiles-related exceptions."""


class HoymilesConnectionError(HoymilesError):
    """Modbus TCP connection could not be established or was reset."""


class HoymilesTimeoutError(HoymilesError):
    """A Modbus request did not complete within the allotted timeout."""


class HoymilesProtocolError(HoymilesError):
    """The DTU returned a malformed Modbus response (size mismatch, exception code, ...)."""


class HoymilesDecodeError(HoymilesError):
    """The raw payload could not be decoded into an InverterReading.

    Typically raised when the byte length does not match INVERTER_PAYLOAD_BYTES,
    or when struct.unpack fails on truncated data.
    """
