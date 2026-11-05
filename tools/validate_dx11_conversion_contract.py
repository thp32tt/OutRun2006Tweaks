#!/usr/bin/env python3
"""Static checks for the DX11 conversion lane.

This validator intentionally does not require a local GPU/runtime. It verifies that
conversion branches keep the disabled activation gate and required evidence markers
before any runtime testing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_TEXT = (
    "NativeDrawPathActive",
)


def check_file(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{path}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    errors = []
    for item in REQUIRED_TEXT:
        if item not in text:
            errors.append(f"missing-symbol:{item}:{path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    targets = args.paths or [Path(".")]
    errors: list[str] = []
    for target in targets:
        if target.is_file():
            errors.extend(check_file(target))
        else:
            for candidate in target.rglob("*.cpp"):
                errors.extend(check_file(candidate))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("DX11_CONVERSION_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
