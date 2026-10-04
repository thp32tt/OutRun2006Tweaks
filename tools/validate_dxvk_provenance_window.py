#!/usr/bin/env python3
"""Validate bounded DXVK raw provenance windows without semantic promotion.

This helper checks evidence shape only:
- RVA range continuity
- overlap byte encoding
- branch target formatting
- optional exact overlap expectations

It does not infer renderer, HUD, or runtime behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _validate_hex_bytes(value: str, label: str, errors: list[str]) -> None:
    tokens = value.split()
    if any(len(token) != 2 for token in tokens):
        errors.append(f"invalid {label} byte width")
    elif any(any(char not in "0123456789abcdefABCDEF" for char in token) for token in tokens):
        errors.append(f"invalid {label} byte encoding")


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    start = record.get("start_rva")
    end = record.get("end_rva")
    if not isinstance(start, str) or not isinstance(end, str):
        errors.append("missing RVA boundary")
        return errors
    try:
        if int(start, 16) >= int(end, 16):
            errors.append("invalid RVA ordering")
    except ValueError:
        errors.append("invalid RVA encoding")

    overlap = record.get("overlap_bytes")
    if overlap is not None:
        if not isinstance(overlap, str):
            errors.append("overlap_bytes must be text")
        else:
            _validate_hex_bytes(overlap, "overlap", errors)

    targets = record.get("branch_targets", [])
    if not isinstance(targets, list):
        errors.append("branch_targets must be a list")
    elif any(not isinstance(target, str) or "->" not in target for target in targets):
        errors.append("invalid branch target format")

    expected = record.get("required_overlap_bytes")
    if expected is not None:
        if not isinstance(expected, str):
            errors.append("required_overlap_bytes must be text")
        else:
            _validate_hex_bytes(expected, "required overlap", errors)
            if overlap != expected:
                errors.append("required overlap bytes mismatch")

    if record.get("semantic_promotion", False) is True:
        errors.append("semantic promotion is forbidden for provenance-only evidence")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    errors = validate(json.loads(args.record.read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print(error)
        return 1
    print("DXVK_PROVENANCE_WINDOW_STATIC_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
