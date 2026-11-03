#!/usr/bin/env python3
"""Validate DXVK raw disassembly continuation overlap windows.

This is a byte-provenance helper only. It does not decode x86 instructions or
promote runtime/render semantics. It rejects gaps or mismatched overlap bytes
when a later evidence window continues a previously captured window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def compact_hex(value: str) -> str:
    return "".join(value.split()).lower()


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    previous = record.get("previous_bytes")
    overlap = record.get("overlap_bytes")
    current = record.get("current_bytes")

    if not all(isinstance(v, str) for v in (previous, overlap, current)):
        return ["byte fields must be hex strings"]

    previous_hex = compact_hex(previous)
    overlap_hex = compact_hex(overlap)
    current_hex = compact_hex(current)

    if not overlap_hex:
        errors.append("overlap bytes cannot be empty")
    if not previous_hex.endswith(overlap_hex):
        errors.append("previous window does not end with overlap")
    if not current_hex.startswith(overlap_hex):
        errors.append("current window does not start with overlap")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    errors = validate(json.loads(Path(args.record).read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print(error)
        return 1
    print("DXVK continuation overlap: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
