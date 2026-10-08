#!/usr/bin/env python3
"""Fail-closed validator for exact DXVK disassembly continuation windows.

This tool intentionally validates byte provenance only. It does not infer runtime
or rendering semantics from a partial disassembly window.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


DEFAULT_OVERLAP = "66 0f 54 1d 20 91 61"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_window(data: bytes, start: int, end: int, overlap: str) -> list[str]:
    errors: list[str] = []
    if start < 0 or end <= start:
        errors.append("invalid_window_range")
        return errors
    if end > len(data):
        errors.append("window_outside_binary")
    if bytes.fromhex(overlap) not in data[start:min(end, len(data))]:
        errors.append("overlap_not_present")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--start", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--end", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--overlap", default=DEFAULT_OVERLAP)
    args = parser.parse_args()

    errors = validate_window(args.binary.read_bytes(), args.start, args.end, args.overlap)
    print({"binary_sha256": sha256_file(args.binary), "errors": errors, "runtime_validation": "UNTESTED"})
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
