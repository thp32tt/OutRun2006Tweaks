#!/usr/bin/env python3
"""DX11 conversion static selector contract check (R202).

Repository-only validation helper. This does not activate the native draw path
and does not represent Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_CROSS_LANE_MARKERS = (
    "korean-localization-clean",
    "vr-dxvk-r71-disasm",
)

REQUIRED_DX11_MARKERS = (
    "DX11",
    "vr-dx11-native-r71",
)


def main() -> None:
    state_path = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    agents_path = ROOT / "AGENTS.md"

    state = state_path.read_text(encoding="utf-8")
    agents = agents_path.read_text(encoding="utf-8")

    missing = [marker for marker in REQUIRED_DX11_MARKERS if marker not in state]
    if missing:
        raise SystemExit("DX11 selector contract missing: " + ", ".join(missing))

    for marker in FORBIDDEN_CROSS_LANE_MARKERS:
        if marker in state:
            raise SystemExit("DX11 lane isolation drift: " + marker)

    if "DX11 Native is the primary implementation/performance lane" not in agents:
        raise SystemExit("DX11 policy marker missing")

    print("DX11 shader selector static contract R202: PASS")


if __name__ == "__main__":
    main()
