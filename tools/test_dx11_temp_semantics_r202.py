#!/usr/bin/env python3
"""Static regression check for the DX11 fixed-function TEMP semantic contract.

Repository-only check. It verifies that future edits retain the documented
D3D9 fixed-function TEMP assumptions without enabling native draw routing.
Runtime and HMD validation remain outside this test.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    translation = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp").read_text(encoding="utf-8")
    header = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.hpp").read_text(encoding="utf-8")

    required_tokens = [
        "D3DTA_TEMP",
        "RESULTARG",
        "TEMP",
    ]

    combined = translation + "\n" + header
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise SystemExit("DX11 TEMP semantic contract drift: " + ", ".join(missing))

    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    if '"native_draw_path_activation_changed": false' not in state:
        raise SystemExit("DX11 activation boundary changed unexpectedly")

    print("DX11 TEMP semantic contract R202: PASS")


if __name__ == "__main__":
    main()
