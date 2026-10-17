#!/usr/bin/env python3
"""Static DX11 conversion lane invariant audit.

This offline check intentionally does not enable the native draw path. It provides
an inexpensive guard for future source changes by detecting accidental activation
markers in DX11 conversion notes/configuration inputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_MARKERS = (
    "NativeDrawPathActive=true",
    "NATIVE_DRAW_PATH_ACTIVE=1",
    "ENABLE_NATIVE_DRAW_PATH=1",
)


def scan(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                findings.append(f"{path}: forbidden activation marker: {marker}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    findings = scan(args.paths)
    if findings:
        print("DX11_SOURCE_INVARIANT_FAIL")
        print("\n".join(findings))
        return 1

    print("DX11_SOURCE_INVARIANT_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
