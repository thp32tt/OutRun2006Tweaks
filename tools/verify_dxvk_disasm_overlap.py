#!/usr/bin/env python3
"""Validate a DXVK disassembly continuation overlap before semantic promotion.

This checker intentionally performs byte/provenance validation only. It does not
claim function identity or runtime behavior from a partial instruction window.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def normalize_hex_bytes(value: str) -> bytes:
    try:
        return bytes.fromhex(" ".join(value.split()))
    except ValueError as exc:
        raise ValueError("invalid hexadecimal byte sequence") from exc


def validate_overlap(previous: bytes, current: bytes, overlap: bytes) -> bool:
    if not overlap:
        return False
    return previous.endswith(overlap) and current.startswith(overlap)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hex-file", required=True)
    parser.add_argument("--expected-overlap", required=True)
    args = parser.parse_args()

    actual_text = Path(args.hex_file).read_text(encoding="utf-8")
    actual = normalize_hex_bytes(actual_text)
    expected = normalize_hex_bytes(args.expected_overlap)

    if not validate_overlap(actual, actual, expected):
        print("DXVK disassembly overlap: FAIL")
        print(f"expected overlap: {expected.hex(' ')}")
        print(f"actual bytes:     {actual.hex(' ')}")
        return 1

    print("DXVK disassembly overlap: PASS")
    print(f"validated overlap bytes: {expected.hex(' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
