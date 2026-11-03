#!/usr/bin/env python3
"""Validate DXVK disassembly continuation overlap evidence.

This is intentionally a static-only gate. It does not infer function semantics;
it only verifies that a continuation window preserves the required overlap bytes
between two independently captured disassembly ranges.
"""

from __future__ import annotations

import argparse
import sys


def normalize_hex(value: str) -> str:
    return " ".join(value.replace("0x", "").split()).lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--overlap", required=True)
    parser.add_argument("--continuation", required=True)
    parser.add_argument(
        "--minimum-overlap-bytes",
        type=int,
        default=1,
        help="fail closed when evidence does not include enough overlap bytes",
    )
    args = parser.parse_args()

    prefix = normalize_hex(args.prefix)
    overlap = normalize_hex(args.overlap)
    continuation = normalize_hex(args.continuation)
    overlap_byte_count = len(overlap.split())

    if overlap_byte_count < args.minimum_overlap_bytes:
        print("DXVK overlap validation failed: insufficient overlap")
        return 1
    if not prefix.endswith(overlap):
        print("DXVK overlap validation failed: prefix boundary mismatch")
        return 1
    if not continuation.startswith(overlap):
        print("DXVK overlap validation failed: continuation boundary mismatch")
        return 1

    print(
        "DXVK disassembly overlap validation: OK "
        f"overlap_bytes={overlap_byte_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
