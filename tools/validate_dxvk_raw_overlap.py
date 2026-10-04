#!/usr/bin/env python3
"""Validate DXVK static disassembly continuation overlap evidence.

This intentionally validates only byte-window provenance. It does not infer
function ownership, rendering semantics, or runtime behavior.
"""

from __future__ import annotations

import argparse
import sys


EXPECTED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def parse_bytes(value: str) -> bytes:
    cleaned = value.replace("0x", "").replace(",", " ")
    return bytes.fromhex(cleaned)


def validate_window(window: bytes) -> bool:
    """Require the known predecessor/continuation overlap at the window start."""
    return window.startswith(EXPECTED_OVERLAP)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hex_window", help="raw bytes beginning at the overlap RVA")
    args = parser.parse_args()

    window = parse_bytes(args.hex_window)
    if not validate_window(window):
        print("DXVK_RAW_OVERLAP_INVALID")
        return 1

    print("DXVK_RAW_OVERLAP_VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
