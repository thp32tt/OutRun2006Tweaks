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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--window", required=True, help="space separated hex bytes")
    parser.add_argument("--overlap", default="")
    args = parser.parse_args()

    window = normalize_hex(args.window)
    overlap = normalize_hex(args.overlap) if args.overlap else b""

    result = {
        "start_rva": args.start_rva,
        "window_bytes": len(window),
        "overlap_bytes": len(overlap),
        "continuation_overlap_valid": (not overlap) or window.startswith(overlap),
        "semantic_promotion": False,
    }
    result["status"] = "PASS" if result["continuation_overlap_valid"] else "FAIL"
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
