#!/usr/bin/env python3
"""Static DX11 conversion contract checker.

Checks source snapshots for the dangerous state-transition pattern where the
DX11 conversion lane accidentally exposes native draw activation before the
conversion evidence gates are satisfied.

This is intentionally a static repository check. It does not claim runtime
validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_ACTIVE_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
)

REQUIRED_SAFE_MARKERS = (
    "NativeDrawPathActive",
    "UNTESTED",
)


def check_text(text: str) -> list[str]:
    errors: list[str] = []
    for marker in FORBIDDEN_ACTIVE_MARKERS:
        if marker in text:
            errors.append(f"unsafe activation marker found: {marker}")
    for marker in REQUIRED_SAFE_MARKERS:
        if marker not in text:
            errors.append(f"missing conversion contract marker: {marker}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    for path in args.paths:
        if not path.exists():
            errors.append(f"missing path: {path}")
            continue
        errors.extend(f"{path}: {e}" for e in check_text(path.read_text(encoding="utf-8", errors="ignore")))

    if errors:
        print("DX11_STATE_TRANSITION_CONTRACT=FAIL")
        for error in errors:
            print(error)
        return 1

    print("DX11_STATE_TRANSITION_CONTRACT=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
