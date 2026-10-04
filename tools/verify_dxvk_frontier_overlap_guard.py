#!/usr/bin/env python3
"""Fail-closed verifier for DXVK disassembly frontier overlap evidence.

This small offline verifier keeps continuation handoff evidence deterministic:
- the next window must begin with the validated overlap bytes;
- missing or truncated overlap evidence is rejected;
- no runtime semantics are inferred.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_OVERLAP = "66 0f 54 1d 20 91 61"


def normalize_bytes(value: str) -> str:
    return " ".join(value.lower().split())


def verify(report: dict[str, object]) -> tuple[bool, str]:
    overlap = report.get("overlap_bytes")
    if not isinstance(overlap, str):
        return False, "missing overlap_bytes"
    if normalize_bytes(overlap) != EXPECTED_OVERLAP:
        return False, "unexpected overlap_bytes"

    start = report.get("provenance_start_rva")
    end = report.get("probe_end_rva")
    if not isinstance(start, str) or not isinstance(end, str):
        return False, "missing provenance range"

    if report.get("predecessor_exact") is not True:
        return False, "predecessor_exact must be true"

    return True, "DXVK frontier overlap evidence: OK"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    ok, message = verify(report)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
