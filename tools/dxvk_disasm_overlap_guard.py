#!/usr/bin/env python3
"""Validate DXVK disassembly continuation windows without promoting semantics.

This helper only checks byte-window continuity. It deliberately does not decode
instructions or claim runtime behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_window(data: bytes, overlap: bytes) -> dict:
    return {
        "window_bytes": len(data),
        "overlap_expected": overlap.hex(" "),
        "overlap_present": data.startswith(overlap),
        "tail_bytes": max(0, len(data) - len(overlap)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("window", type=Path)
    parser.add_argument("--overlap", required=True)
    args = parser.parse_args()

    result = validate_window(args.window.read_bytes(), bytes.fromhex(args.overlap))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["overlap_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
