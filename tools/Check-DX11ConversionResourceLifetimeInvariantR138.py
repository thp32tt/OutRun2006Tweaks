#!/usr/bin/env python3
"""Static guard for DX11 conversion resource lifetime invariants.

This check is intentionally source-tree based. It does not activate the native
DX11 draw path and does not provide runtime validation.
"""

from pathlib import Path
import sys

REQUIRED_MARKERS = (
    "release",
    "reset",
    "device",
    "destroy",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    candidates = list(root.glob("src/**/*.cpp")) + list(root.glob("src/**/*.hpp"))
    if not candidates:
        print("NO_SOURCE_TREE=SKIP")
        return 0

    text = "\n".join(path.read_text(errors="ignore") for path in candidates)
    lowered = text.lower()
    missing = [marker for marker in REQUIRED_MARKERS if marker not in lowered]

    if missing:
        print("RESOURCE_LIFETIME_MARKERS_MISSING=" + ",".join(missing))
        return 1

    print("DX11_RESOURCE_LIFETIME_INVARIANT=PASS_STATIC_ONLY")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
