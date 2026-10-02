#!/usr/bin/env python3
"""Static guard for the DX11 conversion lane continuation contract.

This intentionally does not enable native draw activation.  It verifies that
conversion automation keeps an explicit source/static next action and that the
runtime-only gate remains separate from offline validation.
"""

from pathlib import Path


STATE = Path("docs/CONVERSION_LANE_STATE.json")


def main() -> int:
    text = STATE.read_text(encoding="utf-8")
    required = (
        '"runtime_validation": "UNTESTED"',
        '"independent_static_next_action"',
        '"native_draw_path_activation_changed": false',
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit("missing DX11 conversion safety markers: " + ", ".join(missing))
    print("DX11_CONVERSION_NEXT_ACTION_GUARD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
