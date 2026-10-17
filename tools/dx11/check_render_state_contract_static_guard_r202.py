#!/usr/bin/env python3
"""Static DX11 conversion guard for render-state contract evidence.

This check is source-only. It verifies that the DX11 lane keeps the dormant
conversion path explicit about required state-contract markers without claiming
runtime or HMD validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_MARKERS = (
    "NativeDrawPathActive",
    "false",
)

FORBIDDEN_ENABLE_MARKERS = (
    "NativeDrawPathActive=true",
    "NATIVE_DRAW_PATH_ACTIVE=1",
    "activate_without_validation",
)


def inspect_source(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []

    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    failures.extend(f"missing contract marker: {marker}" for marker in missing)

    for marker in FORBIDDEN_ENABLE_MARKERS:
        if marker in text:
            failures.append(f"unexpected dormant-path bypass marker: {marker}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="DX11 render state static contract guard")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    failures = inspect_source(args.source)
    if failures:
        for failure in failures:
            print(failure)
        return 1

    print("DX11 render state contract static guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
