#!/usr/bin/env python3
"""Static DX11 conversion lane scope validator.

Checks source manifests/config snippets for accidental cross-backend promotion.
This is intentionally offline: runtime validation remains a separate hardware step.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


FORBIDDEN_LANE_MARKERS = (
    "D3D12CreateDevice",
    "D3D12On12",
    "DX12_PROMOTE",
)

REQUIRED_SAFE_MARKERS = (
    "DX11",
    "D3D11",
)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    for marker in FORBIDDEN_LANE_MARKERS:
        if marker in text:
            errors.append(f"forbidden cross-lane marker: {marker}")

    if not any(marker in text for marker in REQUIRED_SAFE_MARKERS):
        errors.append("missing DX11/D3D11 scope marker")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        errors = validate(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}")
        else:
            print(f"{path}: DX11 scope OK")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
