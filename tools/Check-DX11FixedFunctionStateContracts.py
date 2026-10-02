#!/usr/bin/env python3
"""Static guard for DX11 fixed-function conversion contract evidence.

This check is intentionally offline. It validates source/config evidence files for
known dangerous promotion points without enabling the native draw path.
Runtime validation remains outside this tool's scope.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_RUNTIME_ENABLE_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
)

REQUIRED_SAFE_MARKERS = (
    "UNTESTED",
    "NativeDrawPath",
)


def scan(path: Path) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[str] = []

    for marker in FORBIDDEN_RUNTIME_ENABLE_MARKERS:
        if marker in text:
            findings.append(f"runtime activation marker present: {marker}")

    for marker in REQUIRED_SAFE_MARKERS:
        if marker not in text:
            findings.append(f"missing safety evidence marker: {marker}")

    return not findings, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        ok, findings = scan(path)
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {path}")
        for finding in findings:
            print(f"  - {finding}")
        failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
