#!/usr/bin/env python3
"""Decode bounded DXVK disassembly continuation byte windows.

This helper intentionally does not infer runtime semantics. It only preserves
exact byte-window boundaries, overlap bytes, and deterministic instruction
records supplied by an external decoder. It is intended for static evidence
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


@dataclass(frozen=True)
class DecodedRecord:
    rva: int
    size: int
    bytes_hex: str


def make_window(start_rva: int, raw_hex: str) -> ByteWindow:
    """Create a bounded raw evidence window without semantic promotion."""
    data = bytes.fromhex(raw_hex)
    return ByteWindow(start_rva=start_rva, end_rva=start_rva + len(data), data=data)


def overlap_prefix(window: ByteWindow, prefix_hex: str) -> bool:
    """Verify required overlap bytes captured from a previous evidence edge."""
    return window.data.startswith(bytes.fromhex(prefix_hex))


def decode_complete_records(window: ByteWindow, records: list[tuple[int, int]]) -> tuple[DecodedRecord, ...]:
    """Create exact instruction records from externally proven boundaries.

    This deliberately requires the caller to provide instruction boundaries.
    The function validates coverage only; it never guesses x86 instruction
    lengths and never converts bytes into runtime semantics.
    """
    result = []
    for rva, size in records:
        if size <= 0 or not window.contains(rva) or rva + size > window.end_rva:
            raise ValueError("record outside bounded evidence window")
        offset = rva - window.start_rva
        result.append(DecodedRecord(rva, size, window.data[offset:offset + size].hex(" ")))
    return tuple(result)


if __name__ == "__main__":
    sample = make_window(0x182F7E, "66 0f 54 1d 20 91 61")
    print(f"0x{sample.start_rva:08X}-0x{sample.end_rva:08X}: {sample.hex()}")
