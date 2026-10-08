#!/usr/bin/env python3
"""Validate a bounded DXVK raw instruction window without assigning semantics.

This helper is intentionally conservative: it checks that a captured byte window is
non-empty, preserves overlap bytes from a predecessor capture, and records the
exact byte ranges used by a static investigation. It does not decode runtime
behaviour or promote a disassembly guess into a conversion claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_window(data: bytes, start_rva: str, end_rva: str, overlap: bytes | None) -> dict:
    if not data:
        raise ValueError("instruction window is empty")
    if overlap is not None and not data.startswith(overlap):
        raise ValueError("overlap prefix does not match captured window")
    return {
        "start_rva": start_rva,
        "end_rva": end_rva,
        "byte_count": len(data),
        "sha256": sha256_hex(data),
        "overlap_verified": overlap is None or True,
        "semantic_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("window", type=Path)
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    parser.add_argument("--overlap-hex")
    args = parser.parse_args()

    data = args.window.read_bytes()
    overlap = bytes.fromhex(args.overlap_hex) if args.overlap_hex else None
    print(json.dumps(validate_window(data, args.start_rva, args.end_rva, overlap), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
