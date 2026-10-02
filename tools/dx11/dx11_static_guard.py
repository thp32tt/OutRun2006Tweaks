#!/usr/bin/env python3
"""DX11 conversion static guard.

Repository-only validation helper. This intentionally does not enable runtime
activation. It checks source trees for accidental promotion of the native draw
path before exact-build and Quest/VDXR validation exists.
"""

from __future__ import annotations

import argparse
from pathlib import Path


# Keep this list conservative: these are explicit opt-in/runtime forcing
# patterns, not ordinary implementation references.
FORBIDDEN_RUNTIME_ENABLE_MARKERS = (
    "NativeDrawPathActive = true",
    "ENABLE_NATIVE_DRAW_PATH=1",
    "ForceNativeDrawPath",
    "EnableNativeDrawPath(true)",
    "native_draw_activation_override = true",
    "native_draw_path_active: true",
    "nativeDrawPathActive=true",
)

SCANNED_SUFFIXES = {
    ".cpp",
    ".hpp",
    ".h",
    ".c",
    ".ini",
    ".cmake",
    ".py",
    ".ps1",
    ".json",
}


def scan(root: Path) -> int:
    failures = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for marker in FORBIDDEN_RUNTIME_ENABLE_MARKERS:
            if marker in text:
                failures.append((path, marker))

    if failures:
        for path, marker in failures:
            print(f"FAIL: {path}: {marker}")
        return 1

    print("PASS: DX11 native draw activation boundary remains statically guarded")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    return scan(Path(args.root))


if __name__ == "__main__":
    raise SystemExit(main())
