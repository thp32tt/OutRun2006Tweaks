#!/usr/bin/env python3
"""Static guard for DX11 fixed-function conversion contract evidence.

This check is intentionally offline. It validates source/config evidence files for
known dangerous promotion points without enabling the native draw path.
Runtime validation remains outside this tool's scope.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


FORBIDDEN_RUNTIME_ENABLE_PATTERNS = (
    r"NativeDrawPathActive\s*=\s*true",
    r"ENABLE_NATIVE_DRAW_PATH\s*=\s*1",
)

REQUIRED_SAFE_MARKERS = (
    "UNTESTED",
    "NativeDrawPath",
)

SUPPORTED_TEXT_SUFFIXES = {
    ".cpp",
    ".hpp",
    ".h",
    ".ini",
    ".json",
    ".md",
    ".py",
}


def iter_scan_paths(path: Path):
    if path.is_file():
        yield path
        return

    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in SUPPORTED_TEXT_SUFFIXES:
                yield child


def scan(path: Path) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[str] = []

    for pattern in FORBIDDEN_RUNTIME_ENABLE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.append(f"runtime activation marker present: {pattern}")

    for marker in REQUIRED_SAFE_MARKERS:
        if marker not in text:
            findings.append(f"missing safety evidence marker: {marker}")

    return not findings, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    scanned = False
    for root in args.paths:
        for path in iter_scan_paths(root):
            scanned = True
            ok, findings = scan(path)
            status = "PASS" if ok else "FAIL"
            print(f"{status}: {path}")
            for finding in findings:
                print(f"  - {finding}")
            failed |= not ok

    if not scanned:
        print("FAIL: no supported evidence files found")
        return 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
