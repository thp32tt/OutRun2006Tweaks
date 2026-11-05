#!/usr/bin/env python3
"""Static DX11 activation policy contract validator.

Repository-only check for the conversion lane. This does not enable native draw
routing and does not claim Quest 3/VDXR runtime validation.
"""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state_path = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    if state.get("lane") != "DX11":
        raise SystemExit("DX11 lane marker missing")

    if state.get("runtime_validation") != "UNTESTED":
        raise SystemExit("runtime validation must remain separated from static validation")

    next_action = state.get("runtime_next_action", "")
    if "NativeDrawPathActive disabled" not in next_action:
        raise SystemExit("native draw activation gate marker missing")

    if state.get("native_draw_path_activation_changed"):
        raise SystemExit("native draw activation unexpectedly changed")

    forbidden = ("dxvk", "localization")
    policy_text = json.dumps(state).lower()
    for item in forbidden:
        if f'"{item}_modified": true' in policy_text:
            raise SystemExit(f"protected backend scope changed: {item}")

    print("DX11 activation policy contract R204: PASS")


if __name__ == "__main__":
    main()
