#!/usr/bin/env python3
"""Static DX11 activation-boundary regression guard.

Repository-only validation for the DX11 conversion lane. This does not enable the
native draw path and does not claim Quest 3/VDXR runtime validation. It verifies
that future static changes keep the conversion gate explicit.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state_path = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    state = state_path.read_text(encoding="utf-8")

    required = [
        '"lane": "DX11"',
        '"runtime_validation": "UNTESTED"',
        '"native_draw_path_activation_changed": false',
        '"github_only_development": true',
    ]

    missing = [token for token in required if token not in state]
    if missing:
        raise SystemExit(
            "DX11 activation boundary regression drift: " + ", ".join(missing)
        )

    print("DX11 native activation boundary R202: PASS")


if __name__ == "__main__":
    main()
