#!/usr/bin/env python3
"""
DX11 native conversion static guard.

This offline checker is intentionally source-only. It does not activate the
native draw path and it does not replace Quest 3/VDXR runtime validation.
It provides a repeatable CI/manual check for conversion branches by detecting
forbidden accidental activation markers in configuration/source snapshots.
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_FORBIDDEN = (
    "NativeDrawPathActive=true",
    "ENABLE_NATIVE_DRAW_PATH=1",
    "FORCE_NATIVE_DRAW_PATH",
)


def scan(paths: list[Path], forbidden: tuple[str, ...]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in forbidden:
            if token in text:
                findings.append(f"{path}: forbidden activation token: {token}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="DX11 native conversion static guard")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    findings = scan(args.paths, DEFAULT_FORBIDDEN)
    if findings:
        for finding in findings:
            print(finding)
        return 1

    print("DX11_NATIVE_CONVERSION_GUARD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
