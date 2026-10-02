#!/usr/bin/env python3
"""Validate DXVK disassembly continuation evidence overlap.

This is a static evidence helper only. It does not infer runtime semantics.
It verifies that a continuation window preserves the mandatory overlap bytes
captured at the predecessor boundary before a decoder is allowed to consume
following bytes.
"""

from __future__ import annotations

import argparse
import sys


DEFAULT_OVERLAP = "66 0f 54 1d 20 91 61"


def normalize_bytes(value: str) -> bytes:
    compact = value.replace("0x", "").replace(",", " ")
    parts = [p for p in compact.split() if p]
    return bytes(int(p, 16) for p in parts)


def validate_window(overlap: str, window: str) -> tuple[bool, str]:
    expected = normalize_bytes(overlap)
    actual = normalize_bytes(window)
    if len(actual) < len(expected):
        return False, "continuation window shorter than required overlap"
    if actual[: len(expected)] != expected:
        return False, "continuation overlap mismatch"
    return True, "overlap preserved"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlap", default=DEFAULT_OVERLAP)
    parser.add_argument("--window", required=True)
    args = parser.parse_args()

    ok, message = validate_window(args.overlap, args.window)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
