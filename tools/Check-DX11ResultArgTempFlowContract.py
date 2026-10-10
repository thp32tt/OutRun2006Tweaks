#!/usr/bin/env python3
"""
Static guard for DX11 fixed-function combiner conversion.

The native DX11 lane must preserve the D3D9 fixed-function convention where
TEMP is a real dataflow value. This check is intentionally source/static only;
it does not enable native draw routing and it does not claim runtime validation.
"""

from __future__ import annotations

import pathlib
import sys


REQUIRED_MARKERS = (
    "D3DTA_TEMP",
    "RESULTARG",
    "TEMP",
)

FORBIDDEN_ACTIVATION = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
)


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    candidates = list(root.rglob("*.cpp")) + list(root.rglob("*.hpp")) + list(root.rglob("*.py"))

    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in candidates
    )

    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        print("DX11_RESULTARG_TEMP_FLOW=FAIL")
        print("missing=" + ",".join(missing))
        return 1

    active = [marker for marker in FORBIDDEN_ACTIVATION if marker in text]
    if active:
        print("DX11_RESULTARG_TEMP_FLOW=FAIL")
        print("native_activation_marker=" + ",".join(active))
        return 1

    print("DX11_RESULTARG_TEMP_FLOW=PASS")
    print("runtime_validation=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
