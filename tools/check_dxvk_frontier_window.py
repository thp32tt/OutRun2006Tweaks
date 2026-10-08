#!/usr/bin/env python3
"""Small static validator for DXVK disassembly frontier byte windows.

This intentionally validates evidence geometry only. It does not infer runtime,
render, or ownership semantics from raw bytes.
"""

from __future__ import annotations

import argparse
import json


def validate_window(record: dict) -> None:
    start = record.get("start_rva")
    end = record.get("end_rva")
    data = record.get("bytes")
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValueError("start_rva/end_rva must be integers")
    if end < start:
        raise ValueError("end_rva precedes start_rva")
    if not isinstance(data, str):
        raise ValueError("bytes must be a hex string")
    raw = bytes.fromhex(data)
    if start + len(raw) != end:
        raise ValueError("byte window does not match RVA geometry")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    with open(args.record, encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_window(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
