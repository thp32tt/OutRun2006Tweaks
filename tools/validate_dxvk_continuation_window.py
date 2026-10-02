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


DEFAULT_OVERLAP = "66 0f 54 1d 20 91 61"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_window(data: bytes, start: int, end: int, expected_hex: str) -> dict:
    expected = bytes.fromhex(expected_hex)
    actual = data[start : start + len(expected)]
    return {
        "offset": hex(start),
        "end_offset": hex(end),
        "expected_bytes": expected.hex(" "),
        "actual_bytes": actual.hex(" "),
        "matches": actual == expected,
        "available_length": len(actual),
        "window_contains_overlap": start < end and start + len(expected) <= end,
        "window_within_binary": 0 <= start <= end <= len(data),
    }


def validate_runtime_claim(record: dict) -> list[str]:
    errors = []
    if record.get("runtime_validation", "UNTESTED") != "UNTESTED":
        errors.append("runtime_claim_not_allowed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--offset", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--end", type=lambda x: int(x, 0))
    parser.add_argument("--overlap", default=DEFAULT_OVERLAP)
    args = parser.parse_args()

    data = args.binary.read_bytes()
    expected = bytes.fromhex(args.overlap)
    end = args.end if args.end is not None else args.offset + len(expected)
    window = validate_window(data, args.offset, end, args.overlap)
    result = {
        "binary_sha256": sha256_file(args.binary),
        "runtime_validation": "UNTESTED",
        "provenance_only": True,
        "window": window,
    }

    errors = validate_runtime_claim(result)
    if errors:
        result["errors"] = errors
        print(json.dumps(result, indent=2))
        return 1

    if not window["window_within_binary"]:
        result["errors"] = ["window_outside_binary"]
        print(json.dumps(result, indent=2))
        return 1

    if not window["window_contains_overlap"]:
        result["errors"] = ["overlap_outside_declared_window"]
        print(json.dumps(result, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0 if window["matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
