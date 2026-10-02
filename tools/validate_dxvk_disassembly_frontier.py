#!/usr/bin/env python3
"""Static guard for DXVK disassembly frontier evidence.

This validates evidence integrity only. It never infers runtime renderer
semantics and never converts static proof into runtime acceptance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _hex_bytes(value: object) -> bytes:
    if not isinstance(value, str) or not value.strip():
        return b""
    try:
        return bytes.fromhex(value)
    except ValueError:
        return b""


def validate(record: dict) -> list[str]:
    errors: list[str] = []

    start = record.get("provenance_start_rva")
    end = record.get("probe_end_rva")
    if not isinstance(start, str) or not isinstance(end, str):
        errors.append("missing_rva_range")
    else:
        try:
            if int(end, 16) <= int(start, 16):
                errors.append("invalid_rva_range")
        except ValueError:
            errors.append("invalid_rva_encoding")

    overlap = _hex_bytes(record.get("overlap_bytes"))
    if not overlap:
        errors.append("missing_overlap_bytes")

    if record.get("capture_edge_matches") is False:
        errors.append("capture_edge_mismatch")

    instruction_count = record.get("instruction_count")
    if instruction_count is not None and (not isinstance(instruction_count, int) or instruction_count <= 0):
        errors.append("invalid_instruction_count")

    digest = record.get("canonical_exe_sha256")
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64):
        errors.append("invalid_canonical_exe_sha256")

    if record.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_claim_not_allowed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()

    data = json.loads(args.record.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}))
        return 1

    print(json.dumps({"status": "PASS", "runtime_validation": "UNTESTED"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
