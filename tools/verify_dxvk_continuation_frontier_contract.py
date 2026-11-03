#!/usr/bin/env python3
"""Static contract checks for DXVK disassembly continuation frontier records.

This helper intentionally validates evidence shape only. It does not promote
runtime semantics from static disassembly data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FRONTIER_KEYS = (
    "provenance_start_rva",
    "probe_end_rva",
    "overlap_bytes",
    "provenance_status",
    "runtime_validation",
)


def validate_frontier(record: dict) -> list[str]:
    errors: list[str] = []
    frontier = record.get("follow_on_frontier", {})
    for key in REQUIRED_FRONTIER_KEYS:
        if not frontier.get(key):
            errors.append(f"missing follow_on_frontier.{key}")

    if frontier.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_validation must remain UNTESTED for static-only evidence")

    start = frontier.get("provenance_start_rva")
    end = frontier.get("probe_end_rva")
    if start and end and start.lower() >= end.lower():
        errors.append("frontier range is not increasing")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_dxvk_continuation_frontier_contract.py <run-record.json>")
        return 2

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errors = validate_frontier(data)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("DXVK continuation frontier contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
