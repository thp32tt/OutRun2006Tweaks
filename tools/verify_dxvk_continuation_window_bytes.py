#!/usr/bin/env python3
"""Fail-closed validator for DXVK raw disassembly continuation windows.

This utility intentionally validates byte provenance only. It does not infer
function semantics, rendering behavior, or runtime correctness.
"""

from __future__ import annotations

import argparse
import sys


def normalize_hex(value: str) -> str:
    return " ".join(value.split()).lower()


def validate_window(start_rva: str, expected: str, actual: str) -> int:
    if not start_rva.startswith("0x"):
        print("invalid start RVA", file=sys.stderr)
        return 2

    expected_bytes = normalize_hex(expected)
    actual_bytes = normalize_hex(actual)
    if not expected_bytes:
        print("expected byte window is empty", file=sys.stderr)
        return 2

    if actual_bytes != expected_bytes:
        print("DXVK_CONTINUATION_WINDOW_MISMATCH")
        print(f"start={start_rva}")
        print(f"expected={expected_bytes}")
        print(f"actual={actual_bytes}")
        return 1

    print("DXVK_CONTINUATION_WINDOW_PROVEN")
    print(f"start={start_rva}")
    print(f"bytes={expected_bytes}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--actual", required=True)
    args = parser.parse_args()
    return validate_window(args.start_rva, args.expected, args.actual)


if __name__ == "__main__":
    raise SystemExit(main())
