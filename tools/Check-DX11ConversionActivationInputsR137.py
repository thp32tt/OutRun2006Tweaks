#!/usr/bin/env python3
"""Static guard for DX11 conversion activation input boundaries.

This guard keeps the DX11 conversion lane source-only until explicit evidence
exists for activation. It detects accidental enablement tokens in tracked
configuration/evidence files without requiring runtime hardware.
"""

from pathlib import Path
import sys


ACTIVE_MARKERS = (
    "NativeDrawPathActive=true",
    "ENABLE_DX11_NATIVE_EXPERIMENTAL=1",
    "FORCE_NATIVE_DRAW_PATH=1",
)

CONFIG_FILES = (
    "docs/CONVERSION_LANE_STATE.json",
    "OutRun2006Tweaks.ini",
    "CMakeLists.txt",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = []
    content = []

    for name in CONFIG_FILES:
        path = root / name
        if not path.exists():
            missing.append(name)
            continue
        content.append(path.read_text(encoding="utf-8", errors="ignore"))

    if missing:
        print("missing DX11 activation evidence inputs:")
        print("\n".join(missing))
        return 1

    merged = "\n".join(content)
    for marker in ACTIVE_MARKERS:
        if marker in merged:
            print(f"unexpected active conversion marker: {marker}")
            return 1

    print("DX11 activation input boundary PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
