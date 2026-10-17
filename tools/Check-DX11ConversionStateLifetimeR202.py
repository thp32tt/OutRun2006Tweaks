#!/usr/bin/env python3
"""Static guard for DX11 conversion state lifetime invariants.

This check is intentionally source-only. It does not enable NativeDrawPathActive
and does not claim runtime validation. It catches accidental conversion-lane
regressions where persistent DX11 translation state is created without a clear
reset/lifetime boundary marker.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_MARKERS = (
    "NativeDrawPathActive",
    "D3D11",
)

FORBIDDEN_ACTIVE_ENABLE_PATTERNS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    missing = [m for m in REQUIRED_MARKERS if m not in text]
    if missing:
        errors.append(f"missing markers: {', '.join(missing)}")

    for pattern in FORBIDDEN_ACTIVE_ENABLE_PATTERNS:
        if pattern in text:
            errors.append(f"unexpected activation assignment: {pattern}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        errors = check_file(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
