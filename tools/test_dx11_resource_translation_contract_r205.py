#!/usr/bin/env python3
"""Static regression check for DX11 resource translation safety contracts.

This is a repository-only guard. It validates that the native DX11 lane keeps
resource translation helpers present while avoiding activation of the runtime
draw path. Quest 3/VDXR behavior remains a separate runtime validation step.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    resource = (ROOT / "src" / "vr" / "d3d11" / "resource_translation.cpp").read_text(encoding="utf-8")
    header = (ROOT / "src" / "vr" / "d3d11" / "resource_translation.hpp").read_text(encoding="utf-8")
    combined = resource + "\n" + header

    required_tokens = [
        "Resource",
        "D3D11",
        "Translate",
    ]
    missing = [token for token in required_tokens if token not in combined]
    if missing:
        raise SystemExit("DX11 resource translation contract drift: " + ", ".join(missing))

    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    if '"native_draw_path_activation_changed": false' not in state:
        raise SystemExit("DX11 activation boundary changed unexpectedly")

    print("DX11 resource translation contract R205: PASS")


if __name__ == "__main__":
    main()
