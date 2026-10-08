#!/usr/bin/env python3
"""Validate DXVK static disassembly frontier evidence.

This helper checks evidence structure only. It does not infer runtime or
rendering semantics from bytes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    record = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    start = int(record["start_rva"], 16)
    end = int(record["end_rva"], 16)
    overlap = bytes.fromhex(record.get("overlap_bytes", ""))

    checks = {
        "window_order_valid": end > start,
        "overlap_present": bool(overlap),
        "runtime_semantics_promoted": False,
        "static_contract": True,
    }
    result = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": result, "checks": checks}, indent=2))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
