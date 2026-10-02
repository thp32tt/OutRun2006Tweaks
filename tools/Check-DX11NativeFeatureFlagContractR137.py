#!/usr/bin/env python3
"""Static contract guard for DX11 native feature flag boundaries.

This guard is source-only. It prevents accidental activation of dormant DX11
native paths during conversion work. Quest 3/VDXR runtime validation remains
outside this check.
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

TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".h", ".hpp", ".ini", ".json", ".md", ".py", ".txt", ".yml", ".yaml"
}

FORBIDDEN_MARKERS = (
    "NativeDrawPathActive=true",
    "NativeDrawPathActive = true",
    "NATIVE_DRAW_PATH_ACTIVE=true",
    "NATIVE_DRAW_PATH_ACTIVE = true",
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
            if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def check(root: Path) -> int:
    text = collect_text(root)
    failures: list[str] = []

    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            failures.append(f"active native DX11 marker found: {marker}")

    missing = [marker for marker in REQUIRED_BOUNDARY_MARKERS if marker not in text]
    if missing:
        failures.append("DX11 dormant boundary evidence markers missing: " + ", ".join(missing))

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
