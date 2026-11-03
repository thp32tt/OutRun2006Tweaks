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


def load_hex_file(path: str) -> bytes:
    return normalize_hex_bytes(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-file", required=True)
    parser.add_argument("--current-file", required=True)
    parser.add_argument("--expected-overlap", required=True)
    args = parser.parse_args()

    previous = load_hex_file(args.previous_file)
    current = load_hex_file(args.current_file)
    expected = normalize_hex_bytes(args.expected_overlap)

    if not validate_overlap(previous, current, expected):
        print("DXVK disassembly overlap: FAIL")
        print(f"expected overlap: {expected.hex(' ')}")
        return 1

    print("DXVK disassembly overlap: PASS")
    print(f"validated overlap bytes: {expected.hex(' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
