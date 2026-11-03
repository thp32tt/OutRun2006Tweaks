#!/usr/bin/env python3
"""Validate a DXVK disassembly continuation overlap contract.

This is intentionally static-only: it verifies that a captured continuation
starts with the mandatory overlap bytes from the previous proven window before
allowing a report to be consumed by later analysis.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_bytes(value: str) -> str:
    return " ".join(value.lower().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--overlap", required=True)
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    captured = evidence.get("overlap_bytes") or evidence.get("overlapBytes")
    if not isinstance(captured, str):
        raise SystemExit("DXVK_FRONTIER_OVERLAP_MISSING")

    expected = normalize_bytes(args.overlap)
    actual = normalize_bytes(captured)
    if actual != expected:
        raise SystemExit(
            "DXVK_FRONTIER_OVERLAP_MISMATCH "
            f"expected={expected!r} actual={actual!r}"
        )

    print("DXVK frontier overlap contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
