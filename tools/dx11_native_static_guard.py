#!/usr/bin/env python3
"""Small GitHub-only DX11 conversion static guard.

This check is intentionally source based. It does not enable the native draw path
and it does not replace Quest 3/VDXR runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_TOKENS = (
    "Native",
    "D3D11",
)

FORBIDDEN_ACTIVATION_HINTS = (
    "ForceEnableNativeDrawPath",
    "ENABLE_NATIVE_DRAW_PATH=1",
)


def inspect_text(text: str) -> list[str]:
    findings: list[str] = []
    if "D3D11" not in text:
        findings.append("missing D3D11 marker")
    for token in FORBIDDEN_ACTIVATION_HINTS:
        if token in text:
            findings.append(f"unexpected activation hint: {token}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        findings = inspect_text(path.read_text(encoding="utf-8", errors="ignore"))
        if findings:
            failed = True
            print(f"{path}: FAIL")
            for item in findings:
                print(f"  - {item}")
        else:
            print(f"{path}: PASS")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
