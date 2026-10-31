#!/usr/bin/env python3
"""Static guard for DX11 conversion activation boundaries.

This intentionally stays repository-only: it does not require the game, HMD,
or a local DirectX runtime.  It prevents accidental activation changes from
being accepted by source-only validation paths.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_ACTIVE_MARKERS = (
    "NativeDrawPathActive = true",
    "NativeDrawPathActive=true",
)


def main() -> int:
    source = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in (ROOT / "src" / "vr" / "d3d11").rglob("*.cpp")
    )
    for marker in FORBIDDEN_ACTIVE_MARKERS:
        if marker in source:
            raise SystemExit(f"forbidden activation marker found: {marker}")
    print("DX11 activation guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
