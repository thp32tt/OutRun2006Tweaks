#!/usr/bin/env python3
"""Static DX11 conversion input contract guard.

Checks source text manifests/config snapshots used by the DX11 conversion lane
for accidental promotion of runtime activation inputs. This is intentionally a
static guard: it does not claim graphics runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_DEFAULTS = (
    "NativeDrawPathActive=true",
    "EnableNativeDrawPath=true",
    "DX11_NATIVE_ACTIVE=1",
)

REQUIRED_GUARD_MARKERS = (
    "UNTESTED",
    "runtime",
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []
    for token in FORBIDDEN_DEFAULTS:
        if token in text:
            failures.append(f"activation default found: {token}")
    lowered = text.lower()
    if "native" in lowered and not any(m.lower() in lowered for m in REQUIRED_GUARD_MARKERS):
        failures.append("native conversion evidence lacks runtime guard marker")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        errors = check_file(path)
        for error in errors:
            print(f"{path}: {error}")
        failed |= bool(errors)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
