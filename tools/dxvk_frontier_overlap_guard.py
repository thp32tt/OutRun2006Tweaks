#!/usr/bin/env python3
"""Static guard for DXVK disassembly frontier overlap evidence.

This helper intentionally performs no semantic promotion. It only checks that a
continuation window carries the required overlap bytes from its predecessor.
Runtime validation is outside this tool's scope.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_window(data: dict) -> tuple[bool, str]:
    expected = data.get("overlap_bytes")
    actual = data.get("continuation_overlap_bytes")
    if not isinstance(expected, str) or not isinstance(actual, str):
        return False, "missing_overlap_bytes"
    normalize = lambda value: " ".join(value.lower().split())
    if normalize(expected) != normalize(actual):
        return False, "overlap_mismatch"
    if data.get("semantic_promotion") not in (None, "NONE"):
        return False, "semantic_promotion_not_allowed"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    ok, reason = validate_window(payload)
    print(json.dumps({"status": "PASS" if ok else "FAIL", "reason": reason}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
