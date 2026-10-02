#!/usr/bin/env python3
"""DX11 conversion static contract guard R203.

Checks that the conversion lane keeps fixed-function compatibility decisions
explicit in durable state. This is repository-only validation and never claims
Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    required = [
        '"lane": "DX11"',
        '"runtime_validation": "UNTESTED"',
        '"native_draw_path_activation_changed": false',
    ]
    missing = [entry for entry in required if entry not in state]
    if missing:
        raise SystemExit("DX11 R203 contract missing: " + ", ".join(missing))

    print("DX11 fixed function binding contract guard R203: PASS")


if __name__ == "__main__":
    main()
