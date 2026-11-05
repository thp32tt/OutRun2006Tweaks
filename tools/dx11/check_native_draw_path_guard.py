#!/usr/bin/env python3
"""Static guard for DX11 conversion lane native draw-path activation.

The DX11 conversion lane keeps the new path dormant until runtime evidence exists.
This checker provides CI-friendly source/static evidence and does not claim HMD
validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


DISABLED_EVIDENCE = ("NativeDrawPathActive", "false")
BYPASS_MARKERS = (
    "force_enable",
    "activate_without_validation",
    "NativeDrawPathActive=true",
    "NATIVE_DRAW_PATH_ACTIVE=1",
)


def inspect_source(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []

    if not all(marker in text for marker in DISABLED_EVIDENCE):
        failures.append("missing explicit disabled NativeDrawPathActive evidence")

    for marker in BYPASS_MARKERS:
        if marker in text:
            failures.append(f"unexpected activation bypass marker: {marker}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="DX11 dormant path static guard")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    failures = inspect_source(args.source)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: DX11 native draw-path static guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
