#!/usr/bin/env python3
"""Static checks for the DX11 conversion lane.

This intentionally does not activate the native draw path.  It provides a
repeatable source audit for CI/manual review when runtime hardware is not
available.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_RUNTIME_ACTIVATION = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
)

REQUIRED_MARKERS = (
    "D3D11",
)


def scan(root: Path) -> int:
    failures = []
    scanned = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".cpp", ".h", ".hpp", ".cmake", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for marker in FORBIDDEN_RUNTIME_ACTIVATION:
            if marker in text:
                failures.append(f"{path}: forbidden activation marker: {marker}")

    if failures:
        for item in failures:
            print(item)
        return 1

    print(f"DX11 static source guard PASS: scanned={scanned}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="src")
    args = parser.parse_args()
    return scan(Path(args.root))


if __name__ == "__main__":
    sys.exit(main())
