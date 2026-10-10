#!/usr/bin/env python3
"""Static source boundary check for the DX11 conversion lane.

This audit does not enable native rendering and does not claim runtime parity.
It detects accidental activation-style changes in source and keeps the
conversion lane evidence-only until Quest 3/VDXR validation exists.
"""

from pathlib import Path
import sys

ACTIVATION_PATTERNS = (
    "EnableNativeDrawPath(true)",
    "setNativeDrawPathActive(true)",
    "activateNativeDrawPath()",
)

EVIDENCE_MARKERS = (
    "RUNTIME_VALIDATION=UNTESTED",
    "NativeDrawPath",
)


def iter_sources(root: Path):
    for pattern in ("src/**/*.cpp", "src/**/*.hpp", "tools/*.py"):
        yield from root.glob(pattern)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    text = "\n".join(path.read_text(errors="ignore") for path in iter_sources(root))

    missing = [marker for marker in EVIDENCE_MARKERS if marker not in text]
    if missing:
        print("DX11_SOURCE_BOUNDARY_MARKERS_MISSING=" + ",".join(missing))
        return 1

    found = [pattern for pattern in ACTIVATION_PATTERNS if pattern in text]
    if found:
        print("DX11_UNAPPROVED_ACTIVATION_PATTERN=" + ",".join(found))
        return 1

    print("DX11_SOURCE_BOUNDARY_AUDIT=PASS_STATIC_ONLY")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
