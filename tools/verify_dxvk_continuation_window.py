#!/usr/bin/env python3
"""Fail-closed checks for DXVK disassembly continuation byte windows.

This helper validates evidence shape only. It does not promote static
instruction evidence into runtime semantic claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = (
    "start_rva",
    "end_rva",
    "overlap_bytes",
    "instruction_count",
)


def _hex_rva(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing:{field}")

    instruction_count = record.get("instruction_count")
    if not isinstance(instruction_count, int) or instruction_count <= 0:
        errors.append("invalid:instruction_count")

    start = _hex_rva(record.get("start_rva"))
    end = _hex_rva(record.get("end_rva"))
    if start is None or end is None:
        errors.append("invalid:rva-format")
    elif end <= start:
        errors.append("invalid:rva-order")

    overlap = record.get("overlap_bytes")
    if not isinstance(overlap, str) or len(overlap.split()) == 0:
        errors.append("invalid:empty-overlap")

    targets = record.get("branch_targets")
    if targets is not None and not isinstance(targets, list):
        errors.append("invalid:branch-targets-type")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    with args.record.open("r", encoding="utf-8") as handle:
        record = json.load(handle)

    errors = validate(record)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("DXVK_CONTINUATION_WINDOW_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
