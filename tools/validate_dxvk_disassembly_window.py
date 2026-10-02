#!/usr/bin/env python3
"""Validate bounded DXVK disassembly evidence windows.

This tool intentionally performs byte-window bookkeeping only. It does not infer
render/runtime semantics from incomplete disassembly. It helps CI reject
malformed evidence records before promotion to later analysis stages.
"""

from __future__ import annotations

import argparse
import json
import sys


def parse_rva(value: str) -> int:
    return int(value, 0)


def validate(record: dict) -> list[str]:
    errors: list[str] = []

    start = record.get("start_rva")
    end = record.get("end_rva")
    data = record.get("bytes")

    if not isinstance(start, int) or not isinstance(end, int):
        errors.append("start_rva/end_rva must be integers")
    elif end <= start:
        errors.append("end_rva must be greater than start_rva")

    if not isinstance(data, str):
        errors.append("bytes must be a hex string")
    else:
        compact = "".join(data.split())
        if len(compact) % 2:
            errors.append("bytes hex string has odd length")
        elif not all(c in "0123456789abcdefABCDEF" for c in compact):
            errors.append("bytes contains non-hex characters")
        elif isinstance(start, int) and isinstance(end, int):
            expected = end - start
            if len(compact) // 2 != expected:
                errors.append("byte length does not match RVA window length")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", help="JSON evidence record")
    args = parser.parse_args()

    with open(args.record, "r", encoding="utf-8") as handle:
        record = json.load(handle)

    errors = validate(record)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("DXVK_DISASSEMBLY_WINDOW_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
