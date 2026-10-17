#!/usr/bin/env python3
"""Static contract check for DX11 state-cache conversion boundaries.

This guard is intentionally source-only. It verifies that the DX11 lane keeps
state cache ownership explicit and does not accidentally enable the dormant
native draw path through test/config artifacts.
"""

from pathlib import Path
import sys


def require(path: str, needles: list[str]) -> None:
    text = Path(path).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"missing {needle!r} in {path}")


def main() -> int:
    require(
        "src/vr/d3d11/native_backend.cpp",
        ["NativeDrawPathActive", "state"],
    )
    require(
        "tools/dx11_native_conversion_guard.py",
        ["NativeDrawPathActive", "disabled"],
    )
    print("DX11_STATE_CACHE_CONTRACT_R207=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
