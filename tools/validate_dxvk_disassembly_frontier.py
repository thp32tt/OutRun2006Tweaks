#!/usr/bin/env python3
"""Static guard for DXVK disassembly frontier evidence.

This validates evidence integrity only. It never infers runtime renderer
semantics and never converts static proof into runtime acceptance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_hex_bytes(value: object) -> tuple[bytes, bool]:
    if not isinstance(value, str) or not value.strip():
        return b"", False
    try:
        return bytes.fromhex(value), True
    except ValueError:
        return b"", False


def _hex_bytes(value: object) -> bytes:
    return _parse_hex_bytes(value)[0]


def _valid_rva(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("0x"):
        return False
    try:
        return int(value, 16) >= 0
    except ValueError:
        return False


def validate(record: dict) -> list[str]:
    errors: list[str] = []

    start = record.get("provenance_start_rva")
    end = record.get("probe_end_rva")
    if not _valid_rva(start) or not _valid_rva(end):
        errors.append("invalid_rva_encoding")
    elif int(end, 16) <= int(start, 16):
        errors.append("invalid_rva_range")

    overlap, overlap_valid = _parse_hex_bytes(record.get("overlap_bytes"))
    if record.get("overlap_bytes") and not overlap_valid:
        errors.append("invalid_overlap_hex")
    if not overlap:
        errors.append("missing_overlap_bytes")

    payload, payload_valid = _parse_hex_bytes(record.get("bytes"))
    if record.get("bytes") and not payload_valid:
        errors.append("invalid_payload_hex")
    if payload and _valid_rva(start) and _valid_rva(end):
        if len(payload) != int(end, 16) - int(start, 16):
            errors.append("byte_window_length_mismatch")
        if overlap and payload[: len(overlap)] != overlap:
            errors.append("overlap_prefix_mismatch")

    branches = record.get("branch_targets")
    if branches is not None:
        if not isinstance(branches, list) or any(not isinstance(item, str) or "->" not in item for item in branches):
            errors.append("invalid_branch_targets")

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
