#!/usr/bin/env python3
"""Lightweight DX11 conversion static checks.

This tool intentionally avoids runtime GPU requirements. It validates source/config
patterns that commonly regress during D3D9 -> DX11 backend work.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


RULES = (
    (
        "d3d9-device-usage",
        re.compile(r"IDirect3DDevice9|IDirect3DDevice9Ex"),
        "legacy D3D9 device symbols found in DX11-targeted source",
    ),
    (
        "dxgi-present-path",
        re.compile(r"IDXGISwapChain|Present\s*\("),
        "DXGI present path reference",
    ),
    (
        "debug-layer-support",
        re.compile(r"D3D11_CREATE_DEVICE_DEBUG|ID3D11InfoQueue"),
        "D3D11 debug validation support reference",
    ),
)

SOURCE_EXTENSIONS = {".cpp", ".cc", ".c", ".h", ".hpp"}


def scan_file(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"ERROR {path}: {exc}", file=sys.stderr)
        return 1

    hits = 0
    for name, pattern, description in RULES:
        if pattern.search(text):
            print(f"FOUND {name}: {description} ({path})")
            hits += 1
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="DX11 static source guard")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    checked = 0
    findings = 0
    for root in args.paths:
        if root.is_file():
            checked += 1
            findings += scan_file(root)
        elif root.is_dir():
            for path in root.rglob("*"):
                if path.suffix.lower() in SOURCE_EXTENSIONS:
                    checked += 1
                    findings += scan_file(path)

    print(f"DX11_STATIC_CHECK checked={checked} findings={findings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
