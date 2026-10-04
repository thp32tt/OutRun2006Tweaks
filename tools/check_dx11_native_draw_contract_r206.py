#!/usr/bin/env python3
"""Static contract checker for the DX11 native conversion lane.

This intentionally does not enable NativeDrawPathActive.  It verifies that
conversion evidence files and source markers keep the dormant activation gate
explicit until runtime parity evidence exists.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REQUIRED_MARKERS = (
    "NativeDrawPathActive",
    "RUNTIME_VALIDATION",
)


def check_text(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{path}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    return [f"missing-marker:{path}:{m}" for m in missing]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    errors = []
    for path in args.paths:
        errors.extend(check_text(path))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("DX11_NATIVE_DRAW_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
