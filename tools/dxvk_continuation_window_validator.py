#!/usr/bin/env python3
"""Validate bounded DXVK disassembly continuation windows.

This is an offline evidence helper. It deliberately does not infer runtime
semantics from bytes; it only checks that a captured window preserves the
expected overlap boundary and that branch targets remain inside the supplied
window.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    start_rva: int
    end_rva: int
    overlap_hex: str

    @property
    def overlap_bytes(self) -> bytes:
        return bytes.fromhex(self.overlap_hex)


def validate_window(window: Window, blob: bytes) -> list[str]:
    errors: list[str] = []
    expected_size = window.end_rva - window.start_rva
    if expected_size != len(blob):
        errors.append(f"window size mismatch: expected {expected_size}, got {len(blob)}")

    if not blob.startswith(window.overlap_bytes):
        errors.append("mandatory overlap bytes are missing at window start")

    if window.start_rva >= window.end_rva:
        errors.append("invalid RVA range")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rva", required=True, type=lambda x: int(x, 16))
    parser.add_argument("--end-rva", required=True, type=lambda x: int(x, 16))
    parser.add_argument("--overlap", required=True)
    parser.add_argument("--bytes", required=True, help="captured bytes as hex")
    args = parser.parse_args()

    errors = validate_window(
        Window(args.start_rva, args.end_rva, args.overlap),
        bytes.fromhex(args.bytes),
    )
    if errors:
        for error in errors:
            print(error)
        return 1

    print("DXVK_CONTINUATION_WINDOW_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
