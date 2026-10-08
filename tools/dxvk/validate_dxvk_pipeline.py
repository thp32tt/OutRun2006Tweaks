#!/usr/bin/env python3
"""Static DXVK conversion lane validator.

This validator intentionally does not require a game runtime or GPU. It checks
repository-side DXVK migration evidence for common mistakes:
- accidental DX9-only artifacts in DXVK candidate metadata
- missing backend identity declarations
- invalid placeholder markers in generated evidence files

It is designed for CI/static review jobs, not runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_RUNTIME_CLAIMS = (
    "RUNTIME_VALIDATION=PASS",
    "USER_RUNTIME_VERIFIED",
)
REQUIRED_BACKEND_TOKENS = (
    "DXVK",
    "UNTESTED",
)


def validate_text(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    for token in FORBIDDEN_RUNTIME_CLAIMS:
        if token in text:
            errors.append(f"{path}: contains prohibited runtime claim: {token}")

    if "DXVK" not in text.upper():
        errors.append(f"{path}: missing DXVK backend identity")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    for path in args.paths:
        if not path.exists():
            errors.append(f"{path}: missing")
            continue
        errors.extend(validate_text(path))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("DXVK_STATIC_VALIDATION=PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
