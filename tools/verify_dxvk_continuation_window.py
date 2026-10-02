#!/usr/bin/env python3
"""Fail-closed checks for DXVK disassembly continuation byte windows.

This helper intentionally validates evidence shape only. It does not promote
static disassembly into runtime semantic claims.
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


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing:{field}")

    if not isinstance(record.get("instruction_count"), int):
        errors.append("invalid:instruction_count")

    start = record.get("start_rva")
    end = record.get("end_rva")
    if isinstance(start, str) and isinstance(end, str):
        try:
            if int(end, 16) <= int(start, 16):
                errors.append("invalid:rva-order")
        except ValueError:
            errors.append("invalid:rva-format")

    overlap = record.get("overlap_bytes")
    if isinstance(overlap, str):
        if len(overlap.split()) == 0:
            errors.append("invalid:empty-overlap")
    else:
        errors.append("invalid:overlap-type")

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
