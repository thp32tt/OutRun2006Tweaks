#!/usr/bin/env python3
"""Fail-closed checks for DXVK disassembly continuation byte windows.

This helper validates static evidence shape only. It does not promote
instruction bytes into runtime semantic claims.
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
    if not isinstance(value, str) or not value.lower().startswith("0x"):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def _parse_bytes(value: object) -> bytes | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return bytes.fromhex(value)
    except ValueError:
        return None


def _validate_branch_targets(value: object) -> list[str]:
    errors: list[str] = []
    if value is None:
        return errors
    if not isinstance(value, list):
        return ["invalid:branch-targets-type"]

    for index, target in enumerate(value):
        if not isinstance(target, dict):
            errors.append(f"invalid:branch-target-{index}-type")
            continue
        if "rva" not in target:
            errors.append(f"missing:branch-target-{index}-rva")
            continue
        if _hex_rva(target.get("rva")) is None:
            errors.append(f"invalid:branch-target-{index}-rva")
    return errors


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

    overlap = _parse_bytes(record.get("overlap_bytes"))
    if overlap is None:
        errors.append("invalid:overlap-bytes")

    window = record.get("window_bytes")
    if window is not None:
        parsed_window = _parse_bytes(window)
        if parsed_window is None:
            errors.append("invalid:window-bytes")
        elif overlap is not None and not parsed_window.startswith(overlap):
            errors.append("invalid:overlap-mismatch")

    errors.extend(_validate_branch_targets(record.get("branch_targets")))
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
