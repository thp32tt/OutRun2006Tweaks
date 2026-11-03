#!/usr/bin/env python3
"""Validate canonical DXVK disassembly continuation overlap evidence.

This tool intentionally validates evidence boundaries only. It does not infer
runtime/render semantics from incomplete instruction windows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_bytes(value: str) -> str:
    return " ".join(value.split()).lower()


def validate_window(payload: dict) -> list[str]:
    errors: list[str] = []
    for key in ("start_rva", "probe_end_rva", "overlap_bytes"):
        if key not in payload:
            errors.append(f"missing:{key}")

    if errors:
        return errors

    start = int(str(payload["start_rva"]), 16)
    end = int(str(payload["probe_end_rva"]), 16)
    if end <= start:
        errors.append("invalid:rva_range")

    overlap = normalize_bytes(str(payload["overlap_bytes"]))
    if not overlap:
        errors.append("invalid:empty_overlap")

    if not payload.get("predecessor_exact", False):
        errors.append("invalid:predecessor_not_exact")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors = validate_window(payload)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}))
        return 1

    print(json.dumps({"status": "PASS", "scope": "STATIC_DISASSEMBLY_OVERLAP_ONLY"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
