#!/usr/bin/env python3
"""Static guard for DX11 conversion render-state transition contracts.

This check is intentionally source-tree based. It does not enable the native draw
path and does not claim runtime validation. It detects accidental activation of
known unsafe transition markers in conversion metadata and source annotations.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_ACTIVE_MARKERS = (
    "NATIVE_DRAW_PATH_ACTIVE=true",
    "NativeDrawPathActive=true",
    "DX11_NATIVE_DRAW_ENABLED=1",
)

REQUIRED_GUARD_MARKERS = (
    "NativeDrawPathActive",
    "activation",
    "disabled",
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []

    for marker in FORBIDDEN_ACTIVE_MARKERS:
        if marker in text:
            failures.append(f"unsafe activation marker found: {marker}")

    lowered = text.lower()
    if "native" in lowered and "draw" in lowered:
        if not all(marker.lower() in lowered for marker in REQUIRED_GUARD_MARKERS):
            failures.append("native draw references require explicit disabled activation guard")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    for path in args.paths:
        if path.is_file():
            failures.extend(f"{path}: {item}" for item in check_file(path))

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print("DX11 render-state transition contract: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
