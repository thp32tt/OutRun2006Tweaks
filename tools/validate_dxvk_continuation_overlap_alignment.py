#!/usr/bin/env python3
"""Static guard for DXVK disassembly continuation overlap windows.

This tool intentionally validates evidence metadata only. It does not infer
runtime semantics from bytes and does not replace Quest 3/VDXR validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path



def validate(record: dict) -> list[str]:
    errors: list[str] = []

    start = record.get("window_start_rva")
    end = record.get("window_end_rva")
    overlap = record.get("overlap_bytes", "")
    expected = record.get("expected_overlap_bytes", "")

    if not isinstance(start, str) or not start.startswith("0x"):
        errors.append("window_start_rva must be a hex RVA string")
    if not isinstance(end, str) or not end.startswith("0x"):
        errors.append("window_end_rva must be a hex RVA string")

    if isinstance(start, str) and isinstance(end, str):
        try:
            if int(end, 16) <= int(start, 16):
                errors.append("window_end_rva must be after window_start_rva")
        except ValueError:
            errors.append("RVA fields contain invalid hexadecimal values")

    if not overlap:
        errors.append("overlap_bytes must not be empty")
    if expected and overlap.lower() != expected.lower():
        errors.append("overlap_bytes does not match expected_overlap_bytes")

    if record.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_validation must remain UNTESTED for offline evidence")

    return errors



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    args = parser.parse_args()

    with args.metadata.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("PASS: DXVK continuation overlap alignment metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
