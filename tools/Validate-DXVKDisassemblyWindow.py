#!/usr/bin/env python3
"""Validate bounded DXVK disassembly evidence windows.

This tool intentionally does not infer runtime semantics. It only checks that a
captured byte window is contiguous, has the expected overlap prefix, and that
recorded RVA bounds are internally consistent before a report is consumed by
later analysis.
"""

from __future__ import annotations

import argparse
import json
import sys


def parse_hex_bytes(value: str) -> bytes:
    return bytes.fromhex(value.replace("0x", ""))


def validate_window(data: dict) -> list[str]:
    errors: list[str] = []
    try:
        start = int(data["start_rva"], 16)
        end = int(data["end_rva"], 16)
    except (KeyError, ValueError, TypeError):
        errors.append("invalid RVA range")
        return errors

    if end <= start:
        errors.append("RVA end must be greater than start")

    try:
        raw = parse_hex_bytes(data["bytes"])
    except (KeyError, ValueError):
        errors.append("invalid byte payload")
        return errors

    if len(raw) != end - start:
        errors.append("byte length does not match RVA span")

    overlap = data.get("required_overlap")
    if overlap:
        try:
            prefix = parse_hex_bytes(overlap)
            if raw[: len(prefix)] != prefix:
                errors.append("required overlap prefix mismatch")
        except ValueError:
            errors.append("invalid overlap payload")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="JSON evidence window report")
    args = parser.parse_args()

    with open(args.report, encoding="utf-8") as handle:
        report = json.load(handle)

    errors = validate_window(report)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("PASS: DXVK disassembly window contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
