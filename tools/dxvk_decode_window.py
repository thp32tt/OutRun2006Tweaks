#!/usr/bin/env python3
"""Decode bounded DXVK disassembly continuation byte windows.

This helper intentionally does not infer runtime semantics.  It only preserves
exact byte-window boundaries, overlap bytes, and deterministic instruction
records supplied by an external decoder.  It is intended for static evidence
work where partial instruction boundaries must remain visible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ByteWindow:
    start_rva: int
    end_rva: int
    data: bytes

    def contains(self, rva: int) -> bool:
        return self.start_rva <= rva < self.end_rva

    def hex(self) -> str:
        return self.data.hex(" ")


def make_window(start_rva: int, raw_hex: str) -> ByteWindow:
    """Create a bounded raw evidence window without semantic promotion."""
    data = bytes.fromhex(raw_hex)
    return ByteWindow(start_rva=start_rva, end_rva=start_rva + len(data), data=data)


def overlap_prefix(window: ByteWindow, prefix_hex: str) -> bool:
    """Verify required overlap bytes captured from a previous evidence edge."""
    return window.data.startswith(bytes.fromhex(prefix_hex))


if __name__ == "__main__":
    sample = make_window(0x182F7E, "66 0f 54 1d 20 91 61")
    print(f"0x{sample.start_rva:08X}-0x{sample.end_rva:08X}: {sample.hex()}")
