#!/usr/bin/env python3
"""Static guard for DX11 conversion lane native draw-path activation.

This check intentionally does not enable runtime paths. It verifies source text
contains the explicit disabled guard used while Quest 3/VDXR evidence is pending.
It is intended for GitHub CI/static review environments without game hardware.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_DISABLED_MARKERS = (
    "NativeDrawPathActive",
    "false",
)


EXCLUDED_RUNTIME_MARKERS = (
    "force_enable",
    "activate_without_validation",
)


def inspect_source(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []

    if not all(marker in text for marker in REQUIRED_DISABLED_MARKERS):
        failures.append("missing explicit NativeDrawPathActive disabled guard evidence")

    for marker in EXCLUDED_RUNTIME_MARKERS:
        if marker in text:
            failures.append(f"unexpected activation bypass marker: {marker}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
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
