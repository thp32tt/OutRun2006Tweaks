#!/usr/bin/env python3
"""Fail-closed validator for DXVK continuation frontier metadata.

This tool validates static disassembly evidence boundaries only. It does not
interpret renderer behavior or make runtime claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(data: dict) -> tuple[bool, str]:
    required = ("start_rva", "probe_end_rva", "overlap_bytes")
    missing = [key for key in required if not data.get(key)]
    if missing:
        return False, "missing frontier fields: " + ", ".join(missing)

    overlap = str(data["overlap_bytes"]).split()
    if not overlap:
        return False, "empty overlap byte sequence"
    if any(len(byte) != 2 for byte in overlap):
        return False, "invalid overlap byte width"

    return True, "frontier metadata valid"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    args = parser.parse_args()

    with args.metadata.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    ok, message = validate(data)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
