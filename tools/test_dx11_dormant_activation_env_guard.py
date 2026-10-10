#!/usr/bin/env python3
"""Static guard for DX11 conversion activation boundaries.

This check intentionally does not enable NativeDrawPath.  It validates that
conversion tooling keeps activation dependent on explicit evidence markers.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "ACTIVATE_NATIVE_DRAW_PATH=1",
    "DX11_NATIVE_FORCE_ENABLE=1",
)

REQUIRED_DORMANT_MARKERS = (
    "UNTESTED",
    "runtime_validation",
)


def validate_text(text: str) -> list[str]:
    failures: list[str] = []
    for marker in FORBIDDEN:
        if marker in text:
            failures.append(f"forbidden activation marker present: {marker}")
    for marker in REQUIRED_DORMANT_MARKERS:
        if marker not in text:
            failures.append(f"missing dormant evidence marker: {marker}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    failures = validate_text(args.path.read_text(encoding="utf-8"))
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("DX11 dormant activation guard PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
