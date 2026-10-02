#!/usr/bin/env python3
"""Static checks for DX11 conversion lane source boundaries.

This helper intentionally avoids runtime GPU requirements. It catches common
conversion hygiene issues before CI/build review: accidental DXVK/localization
scope leakage and missing DX11 marker references.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_SCOPE_PATHS = (
    "dxvk",
    "localization",
    "korean",
)


def scan(root: Path) -> list[str]:
    failures: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path).replace("\\", "/").lower()
        if any(token in rel for token in FORBIDDEN_SCOPE_PATHS):
            failures.append(f"DX11 lane touched out-of-scope path: {rel}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    failures = scan(Path(args.root))
    if failures:
        for item in failures:
            print(item)
        return 1

    print("DX11_STATIC_SCOPE_GUARD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
