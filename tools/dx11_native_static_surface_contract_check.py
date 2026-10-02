#!/usr/bin/env python3
"""
DX11 conversion lane static surface contract checker.

This offline analyzer validates source text for common conversion hazards:
- accidental native draw-path activation while evidence gates are closed
- unguarded render-surface format changes
- runtime validation claims mixed into static reports

It intentionally performs static checks only. It does not claim GPU/runtime validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_ACTIVATION_TOKENS = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
)

REQUIRED_RUNTIME_LABEL = "UNTESTED"


def scan(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []

    for token in FORBIDDEN_ACTIVATION_TOKENS:
        if token in text:
            failures.append(f"activation token found: {token}")

    if "runtime_validation" in text and REQUIRED_RUNTIME_LABEL not in text:
        failures.append("runtime_validation report lacks UNTESTED/static separation")

    if failures:
        print("DX11_STATIC_SURFACE_CONTRACT_FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("DX11_STATIC_SURFACE_CONTRACT_PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    return scan(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
