#!/usr/bin/env python3
"""Fail-closed verifier for DXVK raw disassembly overlap windows.

This helper intentionally verifies only byte-window geometry. It does not infer
function meaning, rendering behavior, or runtime acceptance.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    start_rva: int
    end_rva: int
    bytes_hex: str

    def size(self) -> int:
        return self.end_rva - self.start_rva


def verify_window(window: Window) -> None:
    payload = bytes.fromhex(window.bytes_hex)
    if not payload:
        raise ValueError("empty overlap payload")
    if window.size() != len(payload):
        raise ValueError(
            f"geometry mismatch: end-start={window.size()} bytes={len(payload)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("start_rva", type=lambda x: int(x, 0))
    parser.add_argument("end_rva", type=lambda x: int(x, 0))
    parser.add_argument("bytes_hex")
    args = parser.parse_args()

    verify_window(Window(args.start_rva, args.end_rva, args.bytes_hex))
    print("DXVK_RAW_OVERLAP_WINDOW=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
