"""Tests for the typed exception hierarchy."""

from __future__ import annotations

import pytest

from custom_components.hoymiles_dtupro.api.exceptions import (
    HoymilesConnectionError,
    HoymilesDecodeError,
    HoymilesError,
    HoymilesProtocolError,
    HoymilesTimeoutError,
)


@pytest.mark.parametrize(
    "subclass",
    [
        HoymilesConnectionError,
        HoymilesTimeoutError,
        HoymilesProtocolError,
        HoymilesDecodeError,
    ],
)
def test_subclasses_inherit_from_base(subclass: type[Exception]) -> None:
    """Every typed exception must inherit from the public base class."""
    assert issubclass(subclass, HoymilesError)


def test_base_inherits_from_exception() -> None:
    """The base class itself is a regular Exception (not BaseException)."""
    assert issubclass(HoymilesError, Exception)


def test_message_is_preserved() -> None:
    """str(exc) returns the message (no fancy reformatting)."""
    err = HoymilesConnectionError("connection refused")
    assert str(err) == "connection refused"


def test_chained_from_underlying_error() -> None:
    """The library is expected to use `raise ... from err` to preserve context."""
    underlying = OSError("network unreachable")
    try:
        raise HoymilesConnectionError("cannot connect") from underlying
    except HoymilesConnectionError as wrapped:
        assert wrapped.__cause__ is underlying
