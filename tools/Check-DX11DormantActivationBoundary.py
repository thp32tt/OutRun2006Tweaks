#!/usr/bin/env python3
"""Static DX11 conversion boundary checker.

This checker intentionally does not activate the native path. It verifies that
conversion work remains behind explicit evidence gates and catches accidental
source markers that would bypass the dormant activation policy.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

FORBIDDEN_ENABLE_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "EnableNativeDrawPath()",
    "ActivateNativeDrawPath()",
)

REQUIRED_GUARD_MARKERS = (
    "RUNTIME_VALIDATION=UNTESTED",
    "NativeDrawPathActive",
)


def scan(root: Path) -> int:
    failures = []
    checked = 0
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".cpp", ".hpp", ".h", ".py", ".ps1", ".md", ".json"}:
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in FORBIDDEN_ENABLE_MARKERS:
            if marker in text:
                failures.append(f"{path}: forbidden activation marker: {marker}")
    if failures:
        print("DX11 dormant activation boundary: FAIL")
        print("\n".join(failures))
        return 1
    print("DX11 dormant activation boundary: PASS")
    print(f"checked_files={checked}")
    print("policy=NativeDrawPathActive remains evidence-gated")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    return scan(Path(args.root))


if __name__ == "__main__":
    sys.exit(main())
