#!/usr/bin/env python3
"""Validate DXVK disassembly continuation windows without semantic promotion.

This helper checks only byte-window continuity and evidence metadata. It
intentionally does not infer render/runtime behavior. It is used for GitHub-only
static evidence checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def normalize_hex(value: str) -> bytes:
    return bytes.fromhex(value.replace("0x", "").replace(",", " "))


def _parse_rva(value: Any, field: str, errors: list[str]) -> int | None:
    try:
        if isinstance(value, bool):
            raise ValueError
        parsed = value if isinstance(value, int) else int(str(value), 0)
    except (TypeError, ValueError):
        errors.append(f"invalid:{field}")
        return None
    if parsed < 0 or parsed > 0xFFFFFFFF:
        errors.append(f"invalid:{field}")
        return None
    return parsed


def _parse_hex_field(record: dict[str, Any], key: str, errors: list[str]) -> bytes | None:
    value = record.get(key, "")
    if not isinstance(value, str):
        errors.append(f"invalid:{key.replace('_', '-')}")
        return None
    try:
        return normalize_hex(value) if value.strip() else b""
    except ValueError:
        errors.append(f"invalid:{key.replace('_', '-')}")
        return None


def validate(record: dict[str, Any]) -> list[str]:
    """Validate one machine-readable continuation evidence record.

    The function is deliberately fail-closed and reports stable error tokens for
    CI/tests. It validates byte/range continuity only; it does not promote any
    function, rendering, HUD, or runtime meaning.
    """

    errors: list[str] = []
    start = _parse_rva(record.get("start_rva"), "start-rva", errors)
    end = _parse_rva(record.get("end_rva"), "end-rva", errors)

    overlap = _parse_hex_field(record, "overlap_bytes", errors)
    window = _parse_hex_field(record, "window_bytes", errors)

    if start is not None and end is not None:
        if end <= start:
            errors.append("invalid:rva-range")
        elif window is not None and len(window) != end - start:
            errors.append("invalid:window-length")

    if overlap is not None and window is not None and overlap and not window.startswith(overlap):
        errors.append("invalid:overlap-mismatch")

    instruction_count = record.get("instruction_count")
    if instruction_count is not None and (
        isinstance(instruction_count, bool)
        or not isinstance(instruction_count, int)
        or instruction_count < 0
    ):
        errors.append("invalid:instruction-count")

    branch_targets = record.get("branch_targets", [])
    if branch_targets is None:
        branch_targets = []
    if not isinstance(branch_targets, list):
        errors.append("invalid:branch-targets")
    else:
        for index, target in enumerate(branch_targets):
            if not isinstance(target, dict):
                errors.append(f"invalid:branch-target-{index}")
                continue
            _parse_rva(target.get("rva"), f"branch-target-{index}-rva", errors)
            if "target_rva" in target:
                _parse_rva(
                    target.get("target_rva"),
                    f"branch-target-{index}-target-rva",
                    errors,
                )

    return errors


def validate_window(start_rva: str, end_rva: str, window: bytes, overlap: bytes) -> dict:
    start = int(start_rva, 0)
    end = int(end_rva, 0)
    checks = {
        "start_rva": start_rva,
        "end_rva": end_rva,
        "window_bytes": len(window),
        "overlap_bytes": len(overlap),
        "range_valid": end > start,
        "range_matches_window": end > start and len(window) == end - start,
        "window_nonempty": bool(window),
        "overlap_matches_prefix": (not overlap) or window.startswith(overlap),
        "semantic_promotion": False,
        "runtime_validation": "UNTESTED",
    }
    checks["status"] = "PASS" if all(
        checks[key]
        for key in (
            "range_valid",
            "range_matches_window",
            "window_nonempty",
            "overlap_matches_prefix",
        )
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
