#!/usr/bin/env python3
"""Static guard for DX11 conversion source reviews.

Checks source text for accidental native draw-path activation and reports
explicit opt-in markers separately from dormant conversion scaffolding.
This tool is intentionally source-only and does not claim runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_DEFAULTS = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
)


ACTIVATION_HINTS = (
    "ENABLE_NATIVE_DRAW_PATH",
    "NativeDrawPathActive",
    "native_draw_path_active",
)


def scan(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    failures = []
    for marker in FORBIDDEN_DEFAULTS:
        if marker in text:
            failures.append(marker)

    hints = [marker for marker in ACTIVATION_HINTS if marker in text]
    if failures:
        print(f"FAIL {path}: default activation markers found")
        for item in failures:
            print(f"  {item}")
        return 1

    print(f"PASS {path}: dormant activation guard clean; hints={len(hints)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    return max(scan(path) for path in args.paths)


if __name__ == "__main__":
    raise SystemExit(main())
