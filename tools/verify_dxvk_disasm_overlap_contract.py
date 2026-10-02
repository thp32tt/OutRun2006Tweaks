#!/usr/bin/env python3
"""Validate DXVK disassembly continuation overlap contracts.

This is an offline evidence guard. It validates byte-window continuity only and
never promotes runtime or rendering semantics.
"""

from __future__ import annotations

EXPECTED_OVERLAP = "66 0f 54 1d 20 91 61"


def normalize_bytes(value: str) -> str:
    return " ".join(value.split()).lower()


def validate_overlap_contract(report: dict) -> list[str]:
    errors: list[str] = []
    if report.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_claim_must_remain_untested")
    if report.get("predecessor_exact") is not True:
        errors.append("predecessor_exact_proof_missing")
    overlap = report.get("overlap_bytes")
    if not isinstance(overlap, str) or normalize_bytes(overlap) != EXPECTED_OVERLAP:
        errors.append("mandatory_overlap_bytes_mismatch")
    return errors


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        result = validate_overlap_contract(json.load(handle))
    raise SystemExit(1 if result else 0)
