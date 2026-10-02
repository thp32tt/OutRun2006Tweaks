#!/usr/bin/env python3
"""Validate exact DXVK continuation raw-window evidence.

This guard checks provenance metadata only. It intentionally does not infer
renderer semantics or runtime behaviour.
"""

from __future__ import annotations

EXPECTED_START = "0x00182F7E"
EXPECTED_END = "0x00182FBE"
EXPECTED_OVERLAP = "66 0f 54 1d 20 91 61"


def normalize_bytes(value: str) -> str:
    return " ".join(value.split()).lower()


def validate_raw_window(report: dict) -> list[str]:
    errors: list[str] = []
    if report.get("runtime_validation") != "UNTESTED":
        errors.append("runtime_validation_must_remain_untested")
    if report.get("provenance_start_rva") != EXPECTED_START:
        errors.append("raw_window_start_mismatch")
    if report.get("probe_end_rva") != EXPECTED_END:
        errors.append("raw_window_end_mismatch")
    if normalize_bytes(report.get("overlap_bytes", "")) != EXPECTED_OVERLAP:
        errors.append("overlap_anchor_mismatch")
    return errors


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        failures = validate_raw_window(json.load(handle))
    raise SystemExit(1 if failures else 0)
