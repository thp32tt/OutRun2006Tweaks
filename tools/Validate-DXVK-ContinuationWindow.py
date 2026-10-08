#!/usr/bin/env python3
"""
Bounded DXVK canonical continuation-window validator.

This tool intentionally validates only static evidence shape. It does not infer
function names, rendering ownership, or runtime behaviour.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


OVERLAP_BYTES = "66 0f 54 1d 20 91 61"


def validate_window(record: dict) -> list[str]:
    errors: list[str] = []
    frontier = record.get("follow_on_frontier", {})

    if frontier.get("provenance_status") != "EXACT_EXE_182F7E_TO_182FBE_PROVENANCE_CAPTURED":
        errors.append("missing exact continuation provenance status")

    if frontier.get("overlap_bytes", "").lower() != OVERLAP_BYTES:
        errors.append("mandatory overlap bytes do not match")

    start = frontier.get("provenance_start_rva")
    end = frontier.get("probe_end_rva")
    if start != "0x00182F7E" or end != "0x00182FBE":
        errors.append("unexpected continuation boundary")

    if record.get("lane") != "DXVK":
        errors.append("record is not a DXVK conversion lane record")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    data = json.loads(args.record.read_text(encoding="utf-8"))
    errors = validate_window(data)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1

    print(json.dumps({"status": "PASS", "scope": "static_continuation_boundary_only"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
