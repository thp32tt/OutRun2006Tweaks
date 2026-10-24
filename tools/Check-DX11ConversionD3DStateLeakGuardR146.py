#!/usr/bin/env python3
"""DX11 conversion static guard R146.

Checks that conversion evidence does not accidentally promote a temporary
D3D9 compatibility state cache into the native DX11 activation path.
This is a source/static contract check only; it does not validate runtime GPU
behaviour.
"""

from pathlib import Path
import sys


FORBIDDEN = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
    "ActivateNativeDrawPath()",
)
REQUIRED = (
    "NativeDrawPathActive",
    "UNTESTED",
)


def scan(root: Path) -> int:
    failures = []
    files = list(root.rglob("*.cpp")) + list(root.rglob("*.h")) + list(root.rglob("*.hpp"))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{path}: forbidden activation token: {token}")
    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1
    print("PASS_STATIC_DX11_D3D_STATE_LEAK_GUARD_R146")
    return 0


if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")))
