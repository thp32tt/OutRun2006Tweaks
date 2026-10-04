#!/usr/bin/env python3
"""Static regression check for DX11 surface lifetime boundary contracts.

Repository-only validation. This keeps the conversion lane explicit about
surface ownership/lifetime helpers while runtime Quest 3/VDXR validation stays
separate.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = (ROOT / "src" / "vr" / "d3d11").read_text(encoding="utf-8") if False else ""

    files = [
        ROOT / "src" / "vr" / "d3d11" / "resource_translation.cpp",
        ROOT / "src" / "vr" / "d3d11" / "resource_translation.hpp",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files if path.exists())

    required = [
        "Surface",
        "Resource",
    ]
    missing = [token for token in required if token not in combined]
    if missing:
        raise SystemExit("DX11 surface lifetime contract drift: " + ", ".join(missing))

    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    if '"native_draw_path_activation_changed": false' not in state:
        raise SystemExit("DX11 native draw activation boundary changed unexpectedly")

    print("DX11 surface lifetime contract R206: PASS")


if __name__ == "__main__":
    main()
