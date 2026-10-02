#!/usr/bin/env python3
"""Static guard for DX11 native conversion activation boundaries.

This check intentionally does not enable the native draw path.  It verifies that
source policy markers continue to require an explicit evidence gate before any
activation change.
"""

from pathlib import Path
import sys

REQUIRED = (
    "NativeDrawPathActive",
    "UNTESTED",
    "runtime_validation",
)

FORBIDDEN_ACTIVATION_MARKERS = (
    "force_native_draw_path=true",
    "AUTO_ENABLE_NATIVE_DRAW_PATH",
    "enable_native_draw_path=true",
)

SCAN_ROOTS = (
    "src/vr/d3d11",
    "vrhost/src",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    state = root / "docs" / "CONVERSION_LANE_STATE.json"
    if not state.exists():
        print("missing conversion lane state")
        return 1

    text = state.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        print("missing required evidence markers:", ", ".join(missing))
        return 1

    sources = []
    for relative in SCAN_ROOTS:
        scan_root = root / relative
        if scan_root.exists():
            sources.extend(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in scan_root.rglob("*")
                if path.is_file()
            )

    source = "\n".join(sources)
    for marker in FORBIDDEN_ACTIVATION_MARKERS:
        if marker in source:
            print("unexpected activation marker:", marker)
            return 1

    if '"runtime_validation": "PASS"' in text:
        print("unexpected runtime validation promotion")
        return 1

    print("DX11 native activation static guard r208 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
