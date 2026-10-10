#!/usr/bin/env python3
"""DX11 conversion-lane static contract checker.

This offline checker is intentionally source-oriented. It does not activate the
native draw path and it does not claim runtime validation. It provides a small
CI-friendly guard for accidental conversion-lane policy regressions.
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

REQUIRED_GUARD_MARKERS = (
    "NativeDrawPathActive",
    "D3D11",
)


def check_text(text: str) -> list[str]:
    errors: list[str] = []
    for marker in FORBIDDEN_ACTIVE_MARKERS:
        if marker in text:
            errors.append(f"forbidden activation marker found: {marker}")
    if not all(marker in text for marker in REQUIRED_GUARD_MARKERS):
        errors.append("DX11 guard context markers missing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    for path in args.paths:
        if not path.exists():
            errors.append(f"missing input: {path}")
            continue
        errors.extend(f"{path}: {err}" for err in check_text(path.read_text(encoding="utf-8", errors="replace")))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("DX11_STATIC_CONTRACT=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
