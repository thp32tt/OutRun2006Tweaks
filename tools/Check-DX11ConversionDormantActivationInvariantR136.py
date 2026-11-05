#!/usr/bin/env python3
"""Static guard for DX11 conversion dormant activation invariants.

This check intentionally does not enable native draw paths. It verifies that
conversion evidence/configuration continues to keep activation explicit and
that accidental promotion markers are absent from tracked text artifacts.
"""

from pathlib import Path
import sys


FORBIDDEN = (
    "NativeDrawPathActive=true",
    "FORCE_NATIVE_DRAW_PATH=1",
    "ENABLE_DX11_NATIVE_EXPERIMENTAL=1",
)

REQUIRED = (
    "NativeDrawPathActive",
)



def main() -> int:
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "docs" / "CONVERSION_LANE_STATE.json",
        root / "CMakeLists.txt",
        root / "OutRun2006Tweaks.ini",
    ]

    missing = [str(p) for p in candidates if not p.exists()]
    if missing:
        print("missing tracked evidence files:")
        print("\n".join(missing))
        return 1

    data = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in candidates)

    for marker in FORBIDDEN:
        if marker in data:
            print(f"forbidden activation marker present: {marker}")
            return 1

    if not any(token in data for token in REQUIRED):
        print("activation boundary marker not found")
        return 1

    print("DX11 dormant activation invariant PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
