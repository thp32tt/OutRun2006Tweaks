#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane continuation contract.

This intentionally does not enable native draw activation. It validates the
machine-readable continuation state instead of relying on text fragments only.
Runtime-only evidence remains separate from offline validation.
"""

import json
from pathlib import Path


STATE = Path("docs/CONVERSION_LANE_STATE.json")


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))

    checks = {
        "runtime_validation": state.get("latest_durable_task", {}).get("runtime_validation") == "UNTESTED",
        "independent_static_next_action": bool(state.get("independent_static_next_action")),
        "native_draw_path_activation_changed": all(
            not unit.get("native_draw_path_activation_changed", True)
            for unit in state.get("completed_static_units", [])
        ),
        "schema_version": state.get("schema_version") == 2,
    }

    missing = [name for name, passed in checks.items() if not passed]
    if missing:
        raise SystemExit("failed DX11 conversion safety checks: " + ", ".join(missing))

    print("DX11_CONVERSION_NEXT_ACTION_GUARD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
