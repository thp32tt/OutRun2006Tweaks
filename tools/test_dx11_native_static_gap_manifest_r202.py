#!/usr/bin/env python3
"""Static DX11 conversion manifest guard.

Keeps the conversion lane's dormant-native-draw safety boundary explicit while
future static work adds new evidence checks. This does not enable runtime paths
and does not represent Quest 3/VDXR validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    run = (ROOT / "docs" / "automation" / "runs" / "CONV-DX11-000001.json").read_text(encoding="utf-8")

    required = [
        '"lane": "DX11"',
        '"runtime_validation": "UNTESTED"',
        '"native_draw_path_activation_changed": false',
        '"selected_work": "DX11_FFP_D3DTA_TEMP_RESULTARG_R200_R201"',
        '"C6_STATE":',
    ]

    missing = [token for token in required if token not in state + run]
    if missing:
        raise SystemExit("DX11 static gap manifest drift: " + ", ".join(missing))

    print("DX11 native static gap manifest R202: PASS")


if __name__ == "__main__":
    main()
