#!/usr/bin/env python3
"""Fail-closed checks for DXVK disassembly continuation frontier metadata.

This helper validates evidence handoff records before a continuation window is
used by static analysis. It intentionally does not infer runtime semantics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_frontier(record: dict) -> list[str]:
    errors: list[str] = []
    frontier = record.get("follow_on_frontier", {})
    required = ("provenance_start_rva", "probe_end_rva", "overlap_bytes")
    for key in required:
        if not frontier.get(key):
            errors.append(f"missing {key}")
    if frontier.get("provenance_status") != "EXACT_EXE_182F7E_TO_182FBE_PROVENANCE_CAPTURED":
        errors.append("frontier provenance is not exact")
    if frontier.get("runtime_validation") != "UNTESTED":
        errors.append("runtime status must remain UNTESTED")
    if not frontier.get("predecessor_exact"):
        errors.append("predecessor proof is not marked exact")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    args = parser.parse_args()
    errors = validate_frontier(json.loads(args.state.read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("DXVK continuation frontier contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
