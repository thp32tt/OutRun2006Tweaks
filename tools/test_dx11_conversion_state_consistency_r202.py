#!/usr/bin/env python3
"""Static consistency guard for the DX11 conversion lane state.

This check intentionally stays repository-only. It verifies that the DX11 lane
has not been silently changed to a runtime-activated or cross-backend state.
Runtime/HMD validation is deliberately not inferred here.
"""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = json.loads(
        (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    )

    assert state["branch"] == "vr-dx11-native-r71"
    assert state["lane"] == "DX11"
    assert state["environment"]["github_only_development"] is True
    assert state["runtime_validation"] == "UNTESTED"
    assert state["policy"]

    forbidden = {
        "dxvk_lane_modified": True,
        "localization_modified": True,
    }
    text = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    for key, value in forbidden.items():
        if f'"{key}": {str(value).lower()}' in text:
            raise SystemExit(f"DX11 lane isolation drift: {key}")

    print("DX11 conversion state consistency R202: PASS")


if __name__ == "__main__":
    main()
