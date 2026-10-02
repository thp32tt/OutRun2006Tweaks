#!/usr/bin/env python3
"""Static contract guard for DX11 native feature flag boundaries.

This guard is intentionally source-only. It verifies that conversion work does
not accidentally turn dormant DX11 native paths into active runtime paths.
Runtime Quest 3/VDXR validation remains outside this check.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCAN_DIRS = (
    "src/vr/d3d11",
    "src",
    "tools",
    "docs",
)

FORBIDDEN_ASSIGNMENTS = (
    "NativeDrawPathActive=true",
    "NativeDrawPathActive = true",
    "NATIVE_DRAW_PATH_ACTIVE=true",
    "NATIVE_DRAW_PATH_ACTIVE = true",
)

FORBIDDEN_ENABLE_CALLS = (
    "EnableNativeDrawPath(true)",
    "enable_native_draw_path(true)",
)

REQUIRED_BOUNDARY_MARKERS = (
    "NativeDrawPathActive",
    "RUNTIME_VALIDATION",
)


def collect_text(root: Path) -> str:
    chunks: list[str] = []
    for directory_name in SCAN_DIRS:
        directory = root / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def check(root: Path) -> int:
    text = collect_text(root)
    failures: list[str] = []

    for marker in FORBIDDEN_ASSIGNMENTS + FORBIDDEN_ENABLE_CALLS:
        if marker in text:
            failures.append(f"active native DX11 marker found: {marker}")

    if not all(marker in text for marker in REQUIRED_BOUNDARY_MARKERS):
        failures.append("DX11 dormant boundary evidence markers missing")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: DX11 native feature flag contract remains dormant")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    sys.exit(check(Path(args.root)))
