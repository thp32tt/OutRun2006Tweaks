#!/usr/bin/env python3
"""Validate bounded DXVK disassembly continuation windows.

This tool intentionally performs provenance checks only. It does not infer
runtime/render semantics from bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_window(data: bytes, start: int, expected_hex: str) -> dict:
    expected = bytes.fromhex(expected_hex)
    actual = data[start : start + len(expected)]
    return {
        "offset": hex(start),
        "expected_bytes": expected.hex(" "),
        "actual_bytes": actual.hex(" "),
        "matches": actual == expected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--offset", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--overlap", required=True)
    args = parser.parse_args()

    result = {
        "binary_sha256": sha256_file(args.binary),
        "runtime_validation": "UNTESTED",
        "provenance_only": True,
        "window": validate_window(args.binary.read_bytes(), args.offset, args.overlap),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["window"]["matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
