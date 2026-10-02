#!/usr/bin/env python3
"""Validate DX11 conversion lane cursor evidence without making runtime claims.

This is a GitHub-only static guard. It verifies that a conversion lane state file
points at the current branch identity, keeps runtime evidence explicit, and does
not accidentally advance a dormant native draw path into activation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_KEYS = (
    "schema_version",
    "branch",
    "lane",
    "latest_durable_task",
    "runtime_validation",
)


def main() -> int:
    state_path = Path("docs/CONVERSION_LANE_STATE.json")
    if not state_path.exists():
        print("FAIL missing conversion lane state")
        return 1

    state = json.loads(state_path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_KEYS if key not in state]
    if missing:
        print("FAIL missing keys: " + ",".join(missing))
        return 1

    if state.get("branch") != "vr-dx11-native-r71":
        print("FAIL branch cursor mismatch")
        return 1

    if state.get("lane") != "DX11":
        print("FAIL lane mismatch")
        return 1

    task = state["latest_durable_task"]
    for key in ("task_id", "result_sha", "validation_bearing_sha"):
        if not task.get(key):
            print("FAIL empty task cursor: " + key)
            return 1

    if state.get("runtime_validation") != "UNTESTED":
        print("FAIL runtime evidence must remain explicit")
        return 1

    if state.get("native_draw_path_activation_changed", False):
        print("FAIL native draw path activation changed")
        return 1

    print("PASS DX11 conversion cursor consistency")
    return 0


if __name__ == "__main__":
    sys.exit(main())
