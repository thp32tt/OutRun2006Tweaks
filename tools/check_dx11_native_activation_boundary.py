#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane activation boundary.

This intentionally does not enable NativeDrawPath. It detects accidental promotion
of dormant DX11 native draw activation paths before Quest 3/VDXR evidence exists.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_PATTERNS = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
    "ENABLE_NATIVE_DRAW_PATH=1",
    "ACTIVATE_NATIVE_DRAW_PATH",
)

REQUIRED_MARKERS = (
    "RUNTIME_VALIDATION",
    "UNTESTED",
)


def scan(root: Path) -> int:
    failures: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".cpp", ".hpp", ".h", ".py", ".json", ".md", ".cmake"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                failures.append(f"{path}: forbidden activation token: {pattern}")

    if failures:
        for failure in failures:
            print(failure)
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    return scan(Path(args.root))


if __name__ == "__main__":
    sys.exit(main())
