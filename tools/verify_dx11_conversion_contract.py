#!/usr/bin/env python3
"""Small GitHub-only static guard for DX11 conversion work.

This does not replace runtime validation. It checks that conversion artifacts keep
important isolation and evidence contracts visible to CI/review automation.
"""
from __future__ import annotations

from pathlib import Path
import sys

REQUIRED = (
    "NativeDrawPathActive",
    "runtime_validation",
)
FORBIDDEN_ACTIVATION = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors = []
    for token in REQUIRED:
        if token not in text:
            errors.append(f"missing contract token: {token}: {path}")
    for token in FORBIDDEN_ACTIVATION:
        if token in text:
            errors.append(f"native activation bypass detected: {token}: {path}")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    candidates = [
        p for p in root.rglob("*.cpp")
        if "dx11" in str(p).lower() or "render" in p.name.lower()
    ]
    errors = []
    for path in candidates:
        errors.extend(check_file(path))
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"DX11_CONVERSION_CONTRACT_PASS files={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
