#!/usr/bin/env python3
"""Small fail-closed helper for DXVK static disassembly windows.

This tool intentionally does not infer runtime semantics.  It keeps the
conversion lane evidence boundary explicit: bytes are decoded into fixed-size
instruction records supplied by an evidence capture, and incomplete trailing
bytes remain visible instead of being silently discarded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DecodeWindow:
    start_rva: int
    raw_hex: str
    expected_end_rva: int


@dataclass(frozen=True)
class ByteWindowResult:
    start_rva: int
    byte_count: int
    end_rva: int
    complete: bool
    trailing_bytes: str


def parse_hex_bytes(raw_hex: str) -> bytes:
    """Parse captured bytes without accepting ambiguous separators."""
    tokens = raw_hex.split()
    if any(len(token) != 2 for token in tokens):
        raise ValueError("hex byte tokens must contain exactly two digits")
    return bytes(int(token, 16) for token in tokens)


def inspect_window(window: DecodeWindow) -> ByteWindowResult:
    data = parse_hex_bytes(window.raw_hex)
    actual_end = window.start_rva + len(data)
    return ByteWindowResult(
        start_rva=window.start_rva,
        byte_count=len(data),
        end_rva=actual_end,
        complete=actual_end >= window.expected_end_rva,
        trailing_bytes="" if actual_end >= window.expected_end_rva else data.hex(" "),
    )


def inspect_many(windows: Iterable[DecodeWindow]) -> list[ByteWindowResult]:
    return [inspect_window(window) for window in windows]


if __name__ == "__main__":
    # Regression guard for the known overlap boundary.  The bytes are evidence,
    # not a semantic decode claim.
    result = inspect_window(
        DecodeWindow(
            start_rva=0x00182F7E,
            raw_hex="66 0f 54 1d 20 91 61",
            expected_end_rva=0x00182FBE,
        )
    )
    assert result.start_rva == 0x00182F7E
    assert result.byte_count == 7
    assert not result.complete
    print(result)
