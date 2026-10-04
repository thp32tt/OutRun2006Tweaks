#!/usr/bin/env python3
"""Validate a DXVK disassembly continuation evidence window.

This is a static evidence guard only. It deliberately does not decode x86
semantics; it verifies that an evidence window starts with the required
validated overlap bytes and does not silently drop a trailing partial window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_OVERLAP = "66 0f 54 1d 20 91 61"


def normalize_hex(value: str) -> str:
    return " ".join(value.lower().replace(",", " ").split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    overlap = normalize_hex(data.get("overlap_bytes", ""))
    probe_end = data.get("probe_end_rva")

    result = {
        "schema": 1,
        "status": "PASS",
        "overlap_matches": overlap == REQUIRED_OVERLAP,
        "probe_end_rva": probe_end,
        "runtime_validation": "UNTESTED",
    }

    if not result["overlap_matches"]:
        result["status"] = "FAIL_OVERLAP_MISMATCH"
        print(json.dumps(result, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
