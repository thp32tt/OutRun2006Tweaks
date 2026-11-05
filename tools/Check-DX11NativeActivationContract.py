#!/usr/bin/env python3
"""Static guard for the DX11 native draw activation contract.

This intentionally does not enable the native path. It checks source/config text
for accidental activation changes and provides a CI-friendly regression probe.
Runtime validation remains outside this tool.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_ENABLE_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "DX11_NATIVE_DRAW_ENABLE=1",
    "force_native_draw_path = true",
)

REQUIRED_DISABLED_MARKERS = (
    "NativeDrawPathActive",
)


def scan(paths: list[Path]) -> int:
    failures: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in FORBIDDEN_ENABLE_MARKERS:
            if marker in text:
                failures.append(f"{path}: forbidden activation marker: {marker}")
    if failures:
        for item in failures:
            print(item)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    return scan(args.paths)


if __name__ == "__main__":
    sys.exit(main())
