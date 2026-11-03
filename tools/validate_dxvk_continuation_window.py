#!/usr/bin/env python3
"""Validate bounded DXVK disassembly continuation windows.

This tool performs provenance checks only. It does not infer runtime/render
semantics from bytes and keeps runtime acceptance explicitly UNTESTED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_OVERLAP = "66 0f 54 1d 20 91 61"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_hex_window(value: str) -> bytes:
    return bytes.fromhex(" ".join(value.split()))


def validate_window(data: bytes, start: int, end: int, expected_hex: str) -> dict:
    expected = parse_hex_window(expected_hex)
    valid_slice = 0 <= start <= end <= len(data)
    actual = data[start : start + len(expected)] if valid_slice else b""
    return {
        "offset": hex(start),
        "end_offset": hex(end),
        "expected_bytes": expected.hex(" "),
        "actual_bytes": actual.hex(" "),
        "matches": actual == expected,
        "available_length": len(actual),
        "expected_length": len(expected),
        "window_contains_overlap": start < end and start + len(expected) <= end,
        "window_within_binary": valid_slice,
    }


def validate_runtime_claim(record: dict) -> list[str]:
    if record.get("runtime_validation", "UNTESTED") != "UNTESTED":
        return ["runtime_claim_not_allowed"]
    return []


def validate_expected_frontier(window: dict) -> list[str]:
    errors = []
    if window["available_length"] != window["expected_length"]:
        errors.append("truncated_frontier_overlap")
    if window["offset"] == window["end_offset"]:
        errors.append("zero_length_frontier_window")
    return errors


def validate_cli_range(start: int, end: int) -> list[str]:
    errors = []
    if start < 0:
        errors.append("negative_window_start")
    if end < 0:
        errors.append("negative_window_end")
    if end < start:
        errors.append("window_end_before_start")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--offset", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--end", type=lambda x: int(x, 0))
    parser.add_argument("--overlap", default=DEFAULT_OVERLAP)
    parser.add_argument("--report", type=Path, help="write machine-readable evidence report")
    args = parser.parse_args()

    data = args.binary.read_bytes()
    expected = parse_hex_window(args.overlap)
    end = args.end if args.end is not None else args.offset + len(expected)
    window = validate_window(data, args.offset, end, args.overlap)
    result = {
        "schema_version": 2,
        "binary_sha256": sha256_file(args.binary),
        "runtime_validation": "UNTESTED",
        "provenance_only": True,
        "semantic_promotion": False,
        "window": window,
    }

    errors = validate_runtime_claim(result)
    errors.extend(validate_cli_range(args.offset, end))
    errors.extend(validate_expected_frontier(window))
    if not window["window_within_binary"]:
        errors.append("window_outside_binary")
    if not window["window_contains_overlap"]:
        errors.append("overlap_outside_declared_window")
    if not window["matches"]:
        errors.append("overlap_bytes_mismatch")

    if errors:
        result["errors"] = errors

    output = json.dumps(result, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
