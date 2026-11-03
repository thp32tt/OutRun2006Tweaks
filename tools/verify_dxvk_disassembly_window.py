#!/usr/bin/env python3
"""Fail-closed verifier for DXVK raw disassembly evidence windows.

This tool validates byte provenance only. It intentionally does not infer
function boundaries, render semantics, or runtime behaviour.
"""

from __future__ import annotations

import argparse
import hashlib
import sys


def normalize_hex(value: str) -> bytes:
    tokens = value.replace("0x", "").replace(",", " ").split()
    if not tokens:
        raise ValueError("empty byte sequence")
    try:
        return bytes(int(token, 16) for token in tokens)
    except ValueError as exc:
        raise ValueError(f"invalid hex byte sequence: {value}") from exc


def verify_window(expected: bytes, actual: bytes, overlap: bytes | None) -> dict[str, object]:
    if len(actual) < len(expected):
        raise ValueError("actual window is shorter than expected evidence")
    if actual[: len(expected)] != expected:
        raise ValueError("canonical byte window mismatch")
    if overlap is not None and not actual.startswith(overlap):
        raise ValueError("mandatory overlap prefix mismatch")

    return {
        "expected_bytes": len(expected),
        "actual_bytes": len(actual),
        "actual_sha256": hashlib.sha256(actual).hexdigest(),
        "overlap_checked": overlap is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True, help="expected canonical bytes")
    parser.add_argument("--actual", required=True, help="captured bytes")
    parser.add_argument("--overlap", help="optional mandatory overlap bytes")
    args = parser.parse_args()

    try:
        result = verify_window(
            normalize_hex(args.expected),
            normalize_hex(args.actual),
            normalize_hex(args.overlap) if args.overlap else None,
        )
    except ValueError as exc:
        print(f"DXVK_DISASSEMBLY_WINDOW_INVALID: {exc}", file=sys.stderr)
        return 1

    for key, value in result.items():
        print(f"{key}={value}")
    print("DXVK_DISASSEMBLY_WINDOW_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
