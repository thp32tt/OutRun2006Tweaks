#!/usr/bin/env python3
"""Static guard for the DX11 conversion activation boundary.

The conversion lane keeps native draw activation disabled until runtime parity
evidence exists. This check only inspects repository source and never claims
Quest 3/VDXR validation.
"""

from pathlib import Path
import sys

FORBIDDEN = (
    "EnableNativeDrawPath(true)",
    "NativeDrawPathActive = true",
    "activate_native_draw_path()",
)

REQUIRED_BOUNDARY = (
    "NativeDrawPath",
    "UNTESTED",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    candidates = list(root.glob("src/**/*.cpp")) + list(root.glob("src/**/*.hpp")) + list(root.glob("tools/*.py"))
    text = "\n".join(path.read_text(errors="ignore") for path in candidates)

    missing = [marker for marker in REQUIRED_BOUNDARY if marker not in text]
    if missing:
        print("DX11_ACTIVATION_BOUNDARY_MARKERS_MISSING=" + ",".join(missing))
        return 1

    found = [marker for marker in FORBIDDEN if marker in text]
    if found:
        print("DX11_NATIVE_ACTIVATION_FORBIDDEN_PATTERN_FOUND=" + ",".join(found))
        return 1

    print("DX11_NATIVE_ACTIVATION_GUARD=PASS_STATIC_ONLY")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
