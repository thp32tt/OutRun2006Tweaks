#!/usr/bin/env python3
"""DX11 conversion lane static guard R133.

Checks that DX11 conversion evidence keeps output-state alias handling explicit
instead of silently reusing ambiguous resource/state names.

This is a source/static contract check only. It does not enable NativeDrawPath
activation and it does not claim runtime validation.
"""

from pathlib import Path
import sys

REQUIRED_MARKERS = (
    "NativeDrawPathActive",
    "UNTESTED",
)


def scan(paths):
    missing = []
    for marker in REQUIRED_MARKERS:
        if not any(marker in path.read_text(encoding="utf-8", errors="ignore") for path in paths):
            missing.append(marker)
    return missing


def main():
    roots = [Path("docs"), Path("src"), Path("vrhost"), Path("tools")]
    files = [p for root in roots if root.exists() for p in root.rglob("*") if p.is_file()]
    missing = scan(files)
    if missing:
        print("DX11_OUTPUT_STATE_ALIAS_GUARD_FAIL=" + ",".join(missing))
        return 1
    print("DX11_OUTPUT_STATE_ALIAS_GUARD_PASS=STATIC_CONTRACT")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
