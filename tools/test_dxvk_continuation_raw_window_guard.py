#!/usr/bin/env python3
"""Static guard for DXVK continuation raw-byte windows.

This intentionally validates only evidence integrity. It does not decode or
promote runtime/render semantics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RawWindow:
    start_rva: int
    end_rva: int
    bytes_hex: str

    @property
    def size(self) -> int:
        return self.end_rva - self.start_rva


def validate_window(window: RawWindow) -> None:
    tokens = window.bytes_hex.split()
    if window.size <= 0:
        raise AssertionError("DXVK raw window must have positive size")
    if len(tokens) == 0:
        raise AssertionError("DXVK raw window cannot be empty")
    if len(tokens) > window.size:
        raise AssertionError("DXVK raw bytes exceed declared RVA window")
    for token in tokens:
        if len(token) != 2:
            raise AssertionError("raw byte tokens must be two hex digits")
        int(token, 16)


def test_required_overlap_prefix() -> None:
    window = RawWindow(
        start_rva=0x00182F7E,
        end_rva=0x00182FBE,
        bytes_hex="66 0f 54 1d 20 91 61",
    )
    validate_window(window)
    assert window.bytes_hex.startswith("66 0f 54")


if __name__ == "__main__":
    test_required_overlap_prefix()
    print("DXVK continuation raw window guard: PASS")
