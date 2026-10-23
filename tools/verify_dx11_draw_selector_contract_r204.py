#!/usr/bin/env python3
"""DX11 static guard for dormant draw selector contract.

Repository-only validation. This does not enable native draw routing and is not
runtime GPU validation. It protects the conversion lane against accidental
selector drift while the native path remains gated.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    candidates = (
        ROOT / "src" / "vr" / "d3d11" / "draw_dispatch.cpp",
        ROOT / "src" / "vr" / "d3d11" / "native_draw.cpp",
    )

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in candidates
        if path.exists()
    )

    required = (
        "NativeDrawPathActive",
        "D3D11",
    )

    missing = [token for token in required if token not in source]
    if missing:
        raise SystemExit(
            "DX11 draw selector contract drift: " + ", ".join(missing)
        )

    print("DX11 draw selector contract R204: PASS")


if __name__ == "__main__":
    main()
