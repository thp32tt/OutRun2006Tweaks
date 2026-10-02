#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane R203 checkpoint.

This verifies that the conversion lane keeps the fixed-function migration
isolated: runtime activation remains disabled, TEMP semantics stay represented,
and the durable task record continues to identify the conversion work item.
It intentionally does not claim runtime or Quest 3/VDXR validation.
"""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = json.loads((ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8"))
    run = json.loads((ROOT / "docs" / "automation" / "runs" / "CONV-DX11-000001.json").read_text(encoding="utf-8"))

    assert state["lane"] == "DX11"
    assert run["selected_work"] == "DX11_FFP_D3DTA_TEMP_RESULTARG_R200_R201"
    assert run["scope_guards"]["native_draw_path_activation_changed"] is False
    assert run["runtime_validation"] == "UNTESTED"
    assert "D3DTA_TEMP" in run["summary"]
    assert run["stages"]["C6_STATE"]["status"] == "COMPLETE_WITH_STATIC_VALIDATION"

    print("DX11 conversion state guard R203: PASS")


if __name__ == "__main__":
    main()
