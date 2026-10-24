#!/usr/bin/env python3
"""DX11 conversion-lane static guard.

Checks source/config text for accidental activation of the native draw path while
conversion evidence is still static-only. This intentionally does not inspect or
modify runtime state.
"""
from __future__ import annotations

import argparse
from pathlib import Path

FORBIDDEN = (
    "NativeDrawPathActive=true",
    "DX11_NATIVE_DRAW_PATH=1",
    "ENABLE_NATIVE_DRAW_PATH=1",
)

SKIP_DIRS = {
    ".git",
    "build",
    "out",
    "dist",
}


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in FORBIDDEN:
            if token in text:
                hits.append(f"{path}:{token}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    hits = scan(Path(args.root))
    if hits:
        print("DX11 activation boundary violation:")
        print("\n".join(hits))
        return 1
    print("DX11 activation boundary static guard PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
