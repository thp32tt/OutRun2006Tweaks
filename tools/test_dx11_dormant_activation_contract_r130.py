#!/usr/bin/env python3
"""Static DX11 conversion guard for dormant native draw activation.

This check intentionally does not enable the DX11 path.  It verifies that
conversion work keeps activation behind an explicit gate while source-level
analysis continues without runtime hardware.
"""

from pathlib import Path
import sys


REQUIRED_SYMBOLS = (
    "NativeDrawPathActive",
    "NativeDrawPath",
)

FORBIDDEN_ENABLE_PATTERNS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
)


def scan_sources(root: Path) -> list[str]:
    hits = []
    for path in root.rglob("*.cpp"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in FORBIDDEN_ENABLE_PATTERNS:
            if pattern in text:
                hits.append(f"{path}:{pattern}")
    return hits


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    hits = scan_sources(root)
    missing = []

    source_text = ""
    for path in root.rglob("*.cpp"):
        try:
            source_text += path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    for symbol in REQUIRED_SYMBOLS:
        if symbol not in source_text:
            missing.append(symbol)

    if missing:
        print("missing DX11 contract symbols:", ", ".join(missing))
        return 1

    if hits:
        print("unexpected native activation assignments:")
        print("\n".join(hits))
        return 1

    print("DX11 dormant activation contract: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
