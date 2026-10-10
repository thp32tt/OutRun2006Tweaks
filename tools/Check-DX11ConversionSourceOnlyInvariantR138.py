#!/usr/bin/env python3
"""Static guard for the DX11 conversion source-only activation boundary.

The DX11 lane may accumulate implementation work while native draw-path
activation remains disabled. This check catches accidental activation tokens
inside tracked source/configuration artifacts without requiring runtime HW.
"""

from pathlib import Path
import sys


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "ENABLE_DX11_NATIVE_EXPERIMENTAL=1",
    "FORCE_NATIVE_DRAW_PATH=1",
    "ActivateNativeDrawPath()",
)

SCAN_ROOTS = (
    "src",
    "tools",
    "CMakeLists.txt",
    "OutRun2006Tweaks.ini",
)


def iter_files(root: Path):
    for item in SCAN_ROOTS:
        path = root / item
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from (p for p in path.rglob("*") if p.is_file())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    checked = 0

    for path in iter_files(root):
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN:
            if marker in text:
                print(f"unexpected DX11 activation marker: {marker} in {path}")
                return 1

    print(f"DX11 source-only invariant PASS ({checked} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
