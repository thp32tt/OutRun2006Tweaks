#!/usr/bin/env python3
"""DX11 conversion static guard for native draw activation boundaries.

Repository-only validation. This guard ensures dormant conversion work does not
silently enable the native draw path before exact-build and Quest 3/VDXR evidence.
"""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = json.loads(
        (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    )

    required = [
        state.get("lane") == "DX11",
        state.get("runtime_validation") == "UNTESTED",
    ]

    if not all(required):
        raise SystemExit("DX11 native draw activation boundary state drift")

    completed = state.get("completed_static_units", [])
    if not isinstance(completed, list):
        raise SystemExit("DX11 completed static unit ledger malformed")

    for unit in completed:
        if unit.get("native_draw_path_activation_changed") is True:
            raise SystemExit("DX11 native draw activation must remain disabled")

    print("DX11 native draw activation boundary R202: PASS")


if __name__ == "__main__":
    main()
