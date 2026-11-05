#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane.

This intentionally does not activate the native draw path. It provides a
repeatable offline check for source review by detecting accidental activation
markers and preserving the conversion gate contract.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_ACTIVE_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH 1",
)

REQUIRED_DISABLED_MARKERS = (
    "NativeDrawPathActive",
)


def scan_text(text: str) -> list[str]:
    findings: list[str] = []
    for marker in FORBIDDEN_ACTIVE_MARKERS:
        if marker in text:
            findings.append(f"forbidden activation marker: {marker}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    checked = 0
    for path in args.paths:
        if not path.exists() or not path.is_file():
            failures.append(f"missing file: {path}")
            continue
        checked += 1
        failures.extend(f"{path}: {item}" for item in scan_text(path.read_text(encoding="utf-8", errors="replace")))

    if failures:
        print("DX11_STATIC_GUARD=FAIL")
        for failure in failures:
            print(failure)
        return 1

    print(f"DX11_STATIC_GUARD=PASS checked={checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
