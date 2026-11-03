#!/usr/bin/env python3
"""Static contract checks for DXVK disassembly frontier evidence records.

This does not prove runtime behavior. It only prevents malformed evidence state
from being mistaken for a completed continuation frontier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_KEYS = {
    "provenance_start_rva",
    "probe_end_rva",
    "overlap_bytes",
    "runtime_validation",
}


def validate_frontier(record: dict) -> None:
    missing = REQUIRED_KEYS - record.keys()
    if missing:
        raise AssertionError(f"missing frontier keys: {sorted(missing)}")
    if record["runtime_validation"] != "UNTESTED":
        raise AssertionError("static frontier evidence must not claim runtime validation")
    if not isinstance(record["overlap_bytes"], str) or not record["overlap_bytes"].strip():
        raise AssertionError("overlap bytes are required for instruction-boundary continuity")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_dxvk_disasm_frontier_contract.py evidence.json")
        return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    validate_frontier(data)
    print("DXVK disassembly frontier contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
