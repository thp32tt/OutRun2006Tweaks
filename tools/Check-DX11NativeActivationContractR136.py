#!/usr/bin/env python3
"""Static guard for the DX11 native conversion activation boundary.

This intentionally checks repository text only. It does not enable the native
path and it is not a runtime validator. The guard catches accidental promotion
of a disabled experimental path during source-only conversion work.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_ACTIVE_MARKERS = (
    "NATIVE_DRAW_PATH_ACTIVE = true",
    "NativeDrawPathActive = true",
    "enable_native_draw_path(true)",
)

REQUIRED_DISABLED_MARKERS = (
    "NativeDrawPathActive",
    "UNTESTED",
)


def scan(root: Path) -> int:
    failures: list[str] = []
    candidates = [
        root / "src/vr/d3d11",
        root / "docs",
        root / "tools",
    ]

    text_files: list[Path] = []
    for directory in candidates:
        if directory.exists():
            text_files.extend(p for p in directory.rglob("*") if p.is_file())

    joined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in text_files
    )

    for marker in FORBIDDEN_ACTIVE_MARKERS:
        if marker in joined:
            failures.append(f"forbidden activation marker found: {marker}")

    if not any(marker in joined for marker in REQUIRED_DISABLED_MARKERS):
        failures.append("expected DX11 conversion boundary markers were not found")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: DX11 native activation contract remains statically gated")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    sys.exit(scan(Path(args.root)))
