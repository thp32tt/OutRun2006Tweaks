#!/usr/bin/env python3
"""Static DX11 conversion guard for fixed-function activation boundaries.

Repository-only check. This does not enable the native draw path and does not
represent Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    pipeline = (ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp").read_text(encoding="utf-8")

    required_state = [
        '"lane": "DX11"',
        '"native_draw_path_activation_changed": false',
        '"runtime_validation": "UNTESTED"',
    ]
    missing = [token for token in required_state if token not in state]
    if missing:
        raise SystemExit("DX11 R202 state contract drift: " + ", ".join(missing))

    required_pipeline = [
        "D3DTA_TEMP",
        "D3DTSS_RESULTARG",
        "D3DTA_SELECTMASK",
    ]
    missing = [token for token in required_pipeline if token not in pipeline]
    if missing:
        raise SystemExit("DX11 R202 fixed-function semantic guard drift: " + ", ".join(missing))

    print("DX11 static contract R202: PASS")


if __name__ == "__main__":
    main()
