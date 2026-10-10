#!/usr/bin/env python3
"""DX11 conversion lane static guard.

Repository-only validation helper. It does not activate the native draw path and
never substitutes runtime Quest 3/VDXR validation.
"""

from pathlib import Path
import argparse
import re
import sys


FORBIDDEN_ACTIVATION_PATTERNS = (
    re.compile(r"NativeDrawPathActive\s*=\s*(true|1)", re.IGNORECASE),
    re.compile(r"native_draw_path_active\s*=\s*(true|1)", re.IGNORECASE),
    re.compile(r"ENABLE_NATIVE_DRAW_PATH\s*=\s*1", re.IGNORECASE),
    re.compile(r"enable_native_draw_path\s*\(\s*true\s*\)", re.IGNORECASE),
)


SCAN_EXTENSIONS = {
    ".cpp", ".c", ".h", ".hpp", ".cmake", ".md", ".json", ".yml", ".yaml", ".ini"
}


def scan(root: Path) -> int:
    failures = []
    checked = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        checked += 1
        for pattern in FORBIDDEN_ACTIVATION_PATTERNS:
            if pattern.search(text):
                failures.append(f"activation marker found: {path}: {pattern.pattern}")

    print(f"DX11_STATIC_GUARD_FILES_CHECKED={checked}")
    if failures:
        print("DX11_STATIC_GUARD_RESULT=FAIL_NATIVE_PATH_ACTIVATION")
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
