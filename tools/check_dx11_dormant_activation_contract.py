#!/usr/bin/env python3
"""Static DX11 conversion-lane contract probe.

This intentionally does not enable the native draw path. It checks repository text
artifacts for accidental promotion markers that would bypass the dormant activation
policy before Quest 3/VDXR evidence exists.

Usage:
    python3 tools/check_dx11_dormant_activation_contract.py [paths...]

Exit code 0 means no forbidden activation markers were found in scanned text.
"""

from __future__ import annotations

import pathlib
import sys

FORBIDDEN_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
)

DEFAULT_ROOTS = ("src", "include", "tools", "docs")
TEXT_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".json", ".md", ".txt"}


def iter_files(roots: list[str]):
    for root in roots:
        path = pathlib.Path(root)
        if path.is_file():
            yield path
        elif path.exists():
            yield from (
                item
                for item in path.rglob("*")
                if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES
            )


def main(argv: list[str]) -> int:
    roots = argv or list(DEFAULT_ROOTS)
    failures = []

    for file_path in iter_files(roots):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                failures.append(f"{file_path}: {marker}")

    if failures:
        print("DX11 dormant activation contract FAILED")
        for failure in failures:
            print(failure)
        return 1

    print("DX11 dormant activation contract PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
