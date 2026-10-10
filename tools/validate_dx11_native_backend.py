#!/usr/bin/env python3
"""Static checks for the DX11 native conversion lane.

This intentionally does not require a Windows runtime or a GPU. It validates
source layout assumptions that are easy to regress while developing the
D3D11/OpenXR host path.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_MARKERS = (
    "ID3D11Device",
    "ID3D11DeviceContext",
)

FORBIDDEN_MARKERS = (
    "D3D12CreateDevice",
    "ID3D12Device",
)


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []

    for marker in REQUIRED_MARKERS:
        if marker not in text:
            errors.append(f"missing DX11 marker: {marker}: {path}")

    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            errors.append(f"unexpected DX12 marker in DX11 lane: {marker}: {path}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    for file_path in args.files:
        if not file_path.exists():
            errors.append(f"missing input: {file_path}")
            continue
        errors.extend(check_file(file_path))

    if errors:
        print("DX11 static validation failed")
        for error in errors:
            print(error)
        return 1

    print("DX11 static validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
