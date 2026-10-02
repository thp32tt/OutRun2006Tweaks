#!/usr/bin/env python3
"""Validate DXVK disassembly continuation windows without semantic promotion.

This helper checks only byte-window continuity. It intentionally does not infer
render/runtime behavior. It is used for GitHub-only static evidence checks.
"""

from __future__ import annotations

import argparse
import json
import sys


def normalize_hex(value: str) -> bytes:
    return bytes.fromhex(value.replace("0x", "").replace(",", " "))


def validate_window(start_rva: str, end_rva: str, window: bytes, overlap: bytes) -> dict:
    start = int(start_rva, 0)
    end = int(end_rva, 0)
    checks = {
        "start_rva": start_rva,
        "end_rva": end_rva,
        "window_bytes": len(window),
        "overlap_bytes": len(overlap),
        "range_valid": end > start,
        "window_nonempty": bool(window),
        "overlap_matches_prefix": (not overlap) or window.startswith(overlap),
        "semantic_promotion": False,
    }
    checks["status"] = "PASS" if all(
        checks[key] for key in ("range_valid", "window_nonempty", "overlap_matches_prefix")
    ) else "FAIL"
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    parser.add_argument("--window", required=True, help="space separated hex bytes")
    parser.add_argument("--overlap", default="")
    args = parser.parse_args()

    result = validate_window(
        args.start_rva,
        args.end_rva,
        normalize_hex(args.window),
        normalize_hex(args.overlap) if args.overlap else b"",
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
