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
        '"github_only_development": true',
        '"runtime_validation": "UNTESTED"',
        '"dxvk_lane_modified": false',
        '"localization_modified": false',
    ]
    missing = [token for token in required if token not in state]
    if missing:
        raise SystemExit("DX11 conversion lane guard drift: " + ", ".join(missing))

    if "DX11 Native is the primary implementation/performance lane" not in agents:
        raise SystemExit("DX11 priority policy marker missing")

    print("DX11 conversion lane guard R201: PASS")


if __name__ == "__main__":
    main()
