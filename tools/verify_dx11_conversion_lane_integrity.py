#!/usr/bin/env python3
"""Static integrity checks for the DX11 conversion lane.

This intentionally avoids runtime assumptions. It verifies that conversion
artifacts keep activation disabled while dormant source translation work is
being developed.
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "CONV-DX11-000001"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"DX11_CONVERSION_INTEGRITY_FAIL: {message}")


def main() -> None:
    state_path = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    run_path = ROOT / "docs" / "automation" / "runs" / f"{TASK_ID}.json"

    require(state_path.exists(), "missing conversion lane state")
    require(run_path.exists(), "missing durable task record")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    run = json.loads(run_path.read_text(encoding="utf-8"))

    require(state.get("lane") == "DX11", "lane mismatch")
    require(state.get("branch") == "vr-dx11-native-r71", "branch mismatch")
    require(run.get("lane") == "DX11", "task lane mismatch")
    require(run.get("task_id") == TASK_ID, "task identity mismatch")
    require(
        run.get("scope_guards", {}).get("native_draw_path_activation_changed") is False,
        "native draw path activation changed unexpectedly",
    )
    require(
        run.get("runtime_validation") == "UNTESTED",
        "runtime state must remain explicitly separated",
    )

    print("DX11_CONVERSION_INTEGRITY_PASS")


if __name__ == "__main__":
    main()
