#!/usr/bin/env python3
"""Fail-closed DXVK continuation-window static contract helper.

Validates a byte window used by DXVK disassembly evidence before any decoder
or report consumes it. This intentionally proves only byte provenance and
boundary safety; it does not infer runtime/render semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_window(data: bytes, start: int, end: int, overlap_hex: str) -> dict:
    expected = bytes.fromhex(overlap_hex)
    actual = data[start : start + len(expected)]
    return {
        "start": start,
        "end": end,
        "matches_overlap": actual == expected,
        "overlap_bytes": len(expected),
        "window_within_binary": 0 <= start <= end <= len(data),
        "overlap_within_window": start + len(expected) <= end,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--offset", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--end", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--overlap", required=True)
    args = parser.parse_args()

    data = args.binary.read_bytes()
    result = {
        "binary_sha256": sha256(data),
        "window": validate_window(data, args.offset, args.end, args.overlap),
    }
    result["status"] = "PASS" if all(result["window"].values()) else "FAIL"
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
