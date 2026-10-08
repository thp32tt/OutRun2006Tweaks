#!/usr/bin/env python3
"""Fail-closed validator for DXVK continuation overlap evidence windows.

This tool intentionally validates evidence shape only. It does not infer runtime
semantics from disassembly bytes.
"""

from __future__ import annotations

import argparse
import json
import sys


REQUIRED_FIELDS = (
    "window_start_rva",
    "window_end_rva",
    "overlap_bytes",
    "predecessor_exact",
)


def parse_rva(value: str) -> int:
    return int(value, 16)


def validate(record: dict) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")

    if errors:
        return errors

    try:
        start = parse_rva(record["window_start_rva"])
        end = parse_rva(record["window_end_rva"])
    except (TypeError, ValueError):
        errors.append("window RVA fields must be hexadecimal strings")
        return errors

    if start >= end:
        errors.append("continuation window must have start RVA below end RVA")

    overlap = record["overlap_bytes"]
    if not isinstance(overlap, str) or len(overlap.split()) == 0:
        errors.append("overlap_bytes must contain decoded hex byte tokens")

    if record["predecessor_exact"] is not True:
        errors.append("predecessor_exact must be true for canonical continuation evidence")

    if record.get("runtime_validation") not in (None, "UNTESTED"):
        errors.append("static evidence validator cannot promote runtime validation")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", help="JSON file containing continuation evidence")
    args = parser.parse_args()

    with open(args.record, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    errors = validate(data)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("DXVK_CONTINUATION_OVERLAP_WINDOW=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
