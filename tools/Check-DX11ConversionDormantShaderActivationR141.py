#!/usr/bin/env python3
"""DX11 conversion dormant shader activation guard.

Static-only check for conversion evidence and shader-path helper inputs. The
conversion lane keeps native draw activation disabled until runtime evidence
exists; this guard catches accidental activation tokens in static artifacts.
It does not claim graphics runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_ACTIVATION_TOKENS = (
    "NativeDrawPathActive=true",
    "EnableNativeDrawPath=true",
    "DX11_NATIVE_ACTIVE=1",
    "ACTIVATE_NATIVE_DRAW_PATH=1",
)

REQUIRED_RUNTIME_SEPARATION = "UNTESTED"


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []

    for token in FORBIDDEN_ACTIVATION_TOKENS:
        if token in text:
            failures.append(f"native activation token found: {token}")

    if "native" in text.lower() and REQUIRED_RUNTIME_SEPARATION.lower() not in text.lower():
        failures.append("native conversion artifact missing UNTESTED runtime separation marker")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        for error in check_file(path):
            print(f"{path}: {error}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
