#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane.

This test intentionally avoids runtime/HMD assumptions. It verifies that conversion
lane metadata keeps native draw activation disabled until evidence gates are met.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "docs" / "CONVERSION_LANE_STATE.json"


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["lane"] == "DX11"
    assert state["environment"]["github_only_development"] is True
    assert state["runtime_blocker"]
    assert state["runtime_next_action"]
    for unit in state.get("completed_static_units", []):
        assert unit.get("native_draw_path_activation_changed") is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
