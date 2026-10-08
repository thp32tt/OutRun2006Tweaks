#!/usr/bin/env python3
"""Validate a DXVK disassembly frontier window before semantic analysis.

This validator intentionally stays byte/provenance based. It does not infer
runtime meaning from incomplete instruction windows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


class FrontierError(ValueError):
    pass


def validate_window(record: dict) -> None:
    required = ("start_rva", "probe_end_rva", "bytes")
    missing = [key for key in required if key not in record]
    if missing:
        raise FrontierError(f"missing fields: {','.join(missing)}")

    start = int(record["start_rva"], 16)
    end = int(record["probe_end_rva"], 16)
    if end <= start:
        raise FrontierError("frontier range is empty or reversed")

    raw = bytes.fromhex(str(record["bytes"]))
    if not raw:
        raise FrontierError("frontier byte window is empty")

    if len(raw) > (end - start):
        raise FrontierError("frontier bytes exceed declared RVA window")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    data = json.loads(args.record.read_text(encoding="utf-8"))
    validate_window(data)
    print("DXVK disassembly frontier validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
