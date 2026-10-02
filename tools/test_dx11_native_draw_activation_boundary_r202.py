#!/usr/bin/env python3
"""DX11 conversion static guard for native draw activation boundaries.

Repository-only validation. This guard ensures dormant conversion work does not
silently enable the native draw path before exact-build and Quest 3/VDXR evidence.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")

    required = [
        '"lane": "DX11"',
        '"native_draw_path_active_changed": false',
        '"runtime_validation": "UNTESTED"',
    ]

    missing = [token for token in required if token not in state]
    if missing:
        raise SystemExit("DX11 native draw activation boundary drift: " + ", ".join(missing))

    forbidden = [
        '"native_draw_path_active_changed": true',
        "NativeDrawPathActive = true",
    ]
    if any(item in state for item in forbidden):
        raise SystemExit("DX11 native draw activation must remain disabled")

    print("DX11 native draw activation boundary R202: PASS")


if __name__ == "__main__":
    main()
