"""Public API for the Hoymiles DTU-Pro async client library.

This package is designed to be importable both:
  * standalone (CLI scripts, future PyPI publication),
  * embedded inside the HA custom_component (`custom_components/hoymiles_dtupro`).

Stability: PoC — APIs may change before v1.0.
"""

from __future__ import annotations

from .client import HoymilesAsyncClient
from .const import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT_S,
    DEFAULT_UNIT_ID,
    DTU_TYPE_LEGACY,
    DTU_TYPE_OPENDTU,
    DTU_TYPE_STANDARD,
)
from .exceptions import (
    HoymilesConnectionError,
    HoymilesDecodeError,
    HoymilesError,
    HoymilesProtocolError,
    HoymilesTimeoutError,
)
from .models import InverterReading, InverterSeries, PlantData

__all__ = [
    # Defaults / constants (curated)
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT_S",
    "DEFAULT_UNIT_ID",
    "DTU_TYPE_LEGACY",
    "DTU_TYPE_OPENDTU",
    "DTU_TYPE_STANDARD",
    # Client
    "HoymilesAsyncClient",
    "HoymilesConnectionError",
    "HoymilesDecodeError",
    # Exceptions
    "HoymilesError",
    "HoymilesProtocolError",
    "HoymilesTimeoutError",
    # Models
    "InverterReading",
    "InverterSeries",
    "PlantData",
]
