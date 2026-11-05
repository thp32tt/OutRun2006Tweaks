#!/usr/bin/env python3
"""DX11 conversion static contract guard R147.

Detects accidental introduction of untracked fixed-function register writes
inside the DX11 translation lane. This is a repository source contract only;
it does not claim GPU or Quest 3/VDXR runtime validation.
"""

from pathlib import Path
import sys


SCAN_SUFFIXES = ("*.cpp", "*.hpp", "*.h", "*.c", "*.inl", "*.inc")
IGNORED_DIRS = {".git", "out", "build", "bin"}
TRACKED_MARKERS = (
    "D3DTA_TEMP",
    "D3DTSS_RESULTARG",
    "NativeDrawPathActive",
)
FORBIDDEN = (
    "TODO_ACTIVATE_NATIVE_DRAW",
    "force_native_draw_path",
)


def iter_sources(root: Path):
    seen = set()
    for pattern in SCAN_SUFFIXES:
        for path in root.rglob(pattern):
            if path in seen:
                continue
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            seen.add(path)
            yield path


def scan(root: Path) -> int:
    failures = []
    seen_marker = False
    scanned = 0

    for path in iter_sources(root):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in text for marker in TRACKED_MARKERS):
            seen_marker = True
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{path}: forbidden contract token: {token}")

    if scanned == 0:
        failures.append("no DX11 source files were scanned")
    if not seen_marker:
        failures.append("DX11 fixed-function translation markers were not found")
    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1
    print(f"PASS_STATIC_DX11_SHADER_REGISTER_CONTRACT_R147 scanned={scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")))
