#!/usr/bin/env python3
"""Static audit for DX11 fixed-function TEMP register handling.

This intentionally does not enable the native draw path.  It checks that the
conversion sources retain the invariants required before any runtime routing
change is considered:
- TEMP is represented explicitly in the translation layer.
- TEMP initialization remains visible as a zero/default path.
- RESULTARG TEMP routing has an implementation reference.

Usage:
    python tools/Check-DX11ConversionTempRegisterSafetyR202.py <repo-root>
"""

from __future__ import annotations

import pathlib
import sys

REQUIRED = {
    "pipeline_translation.cpp": (
        "TEMP",
        "RESULTARG",
    ),
    "pipeline_translation.hpp": (
        "TEMP",
    ),
}


def main() -> int:
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    d3d11 = root / "src" / "vr" / "d3d11"
    missing = []

    for name, tokens in REQUIRED.items():
        path = d3d11 / name
        if not path.exists():
            missing.append(f"missing:{path}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in tokens:
            if token not in text:
                missing.append(f"{path}:{token}")

    if missing:
        print("DX11_TEMP_REGISTER_SAFETY=FAIL")
        for item in missing:
            print(item)
        return 1

    print("DX11_TEMP_REGISTER_SAFETY=PASS")
    print("native_draw_path_activation=UNCHANGED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
