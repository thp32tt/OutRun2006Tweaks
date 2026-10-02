#!/usr/bin/env python3
"""Static regression guard for DX11 conversion lane isolation.

This is intentionally repository-only validation. It does not enable native draw
routing or claim runtime/HMD validation. The guard prevents future conversion
work from accidentally changing protected backend boundaries.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    required = [
        '"lane": "DX11"',
        '"branch": "vr-dx11-native-r71"',
        '"github_only_development": true',
        '"runtime_validation": "UNTESTED"',
        '"dxvk_lane_modified": false',
        '"localization_modified": false',
        '"other_backend_modified": false',
        '"native_draw_path_activation_changed": false',
        '"Keep NativeDrawPathActive disabled."',
        '"Exact-build exhaustive DX11 census and Quest 3/VDXR parity remain required before activation."',
    ]
    missing = [token for token in required if token not in state]
    if missing:
        raise SystemExit("DX11 conversion lane guard drift: " + ", ".join(missing))

    if "DX11 Native is the primary implementation/performance lane" not in agents:
        raise SystemExit("DX11 priority policy marker missing")

    if "DXVK is the secondary implementation/performance lane" not in agents:
        raise SystemExit("backend priority isolation marker missing")

    if "runtime validation" not in agents.lower():
        raise SystemExit("runtime validation policy marker missing")

    print("DX11 conversion lane guard R203: PASS")


if __name__ == "__main__":
    main()
