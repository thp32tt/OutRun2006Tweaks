#!/usr/bin/env python3
"""
DX11 conversion lane static guard.

Repository-only validation helper. It does not activate the native draw path and
never substitutes runtime Quest 3/VDXR validation.
"""

from pathlib import Path
import argparse
import sys


FORBIDDEN_ACTIVATION_MARKERS = (
    "NativeDrawPathActive = true",
    "native_draw_path_active = true",
    "ENABLE_NATIVE_DRAW_PATH=1",
)


def scan(root: Path) -> int:
    failures = []
    checked = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".cpp", ".h", ".hpp", ".cmake", ".md", ".json", ".yml", ".yaml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        checked += 1
        for marker in FORBIDDEN_ACTIVATION_MARKERS:
            if marker in text:
                failures.append(f"activation marker found: {path}: {marker}")

    print(f"DX11_STATIC_GUARD_FILES_CHECKED={checked}")
    if failures:
        for failure in failures:
            print(failure)
        return 1

    print("DX11_STATIC_GUARD_RESULT=PASS_DORMANT_ACTIVATION_SCAN")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    sys.exit(scan(Path(parser.parse_args().root)))
