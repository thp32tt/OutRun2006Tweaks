#!/usr/bin/env python3
"""Validate DXVK static disassembly continuation evidence records.

This validator intentionally stays offline and evidence-only. It does not infer
runtime behaviour from bytes; it checks that a recorded continuation window is
internally consistent before evidence is consumed by later tooling.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CANONICAL_OVERLAP_BYTES = bytes.fromhex("66 0f 54 1d 20 91 61")


def parse_hex_bytes(value: str) -> bytes:
    return bytes.fromhex(value.replace("0x", "").replace(" ", ""))


def validate(record: dict) -> list[str]:
    errors: list[str] = []

    start = record.get("start_rva")
    end = record.get("end_rva")
    blob = record.get("bytes")

    if not isinstance(start, str) or not isinstance(end, str):
        errors.append("missing RVA range")
    else:
        try:
            if int(end, 16) <= int(start, 16):
                errors.append("end_rva must be greater than start_rva")
        except ValueError:
            errors.append("RVA is not hexadecimal")

    if not isinstance(blob, str):
        errors.append("missing byte window")
    else:
        try:
            decoded = parse_hex_bytes(blob)
            if len(decoded) == 0:
                errors.append("byte window is empty")
            if start == "0x182F7E" and not decoded.startswith(CANONICAL_OVERLAP_BYTES):
                errors.append("byte window must preserve canonical overlap bytes")
        except ValueError:
            errors.append("byte window is not valid hex")

    branches = record.get("branch_targets", [])
    if not isinstance(branches, list):
        errors.append("branch_targets must be a list")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    data = json.loads(args.record.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("DXVK_CONTINUATION_EVIDENCE=VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
