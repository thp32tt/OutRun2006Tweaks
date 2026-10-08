#!/usr/bin/env python3
"""Validate bounded DXVK disassembly evidence windows.

This tool intentionally validates byte-window continuity only. It does not infer
runtime/render semantics from incomplete machine-code captures.
"""

from __future__ import annotations

import argparse
import sys


def normalize_hex(value: str) -> bytes:
    return bytes.fromhex(value.replace("0x", "").replace("_", "").replace(" ", ""))


def validate_overlap(previous: str, current: str, overlap: int) -> bool:
    left = normalize_hex(previous)
    right = normalize_hex(current)
    if overlap <= 0:
        raise ValueError("overlap must be positive")
    if len(left) < overlap or len(right) < overlap:
        return False
    return left[-overlap:] == right[:overlap]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", required=True, help="previous captured byte window")
    parser.add_argument("--current", required=True, help="next captured byte window")
    parser.add_argument("--overlap", type=int, required=True)
    args = parser.parse_args()

    if not validate_overlap(args.previous, args.current, args.overlap):
        print("DXVK_DISASM_WINDOW_OVERLAP=FAIL")
        return 1

    print("DXVK_DISASM_WINDOW_OVERLAP=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
