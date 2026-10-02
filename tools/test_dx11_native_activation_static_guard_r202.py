#!/usr/bin/env python3
"""Static DX11 dormant activation guard.

Repository-only validation for the conversion lane. This guard intentionally
checks evidence/config boundaries and never enables native draw activation or
claims Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    required = [
        '"lane": "DX11"',
        '"native_draw_path_activation_changed": false',
        '"runtime_validation": "UNTESTED"',
    ]

    missing = [item for item in required if item not in state]
    if missing:
        raise SystemExit("DX11 dormant activation guard drift: " + ", ".join(missing))

    if '"lane": "DXVK"' in state:
        raise SystemExit("DX11 guard crossed backend boundary")

    print("DX11 dormant activation guard R202: PASS")


if __name__ == "__main__":
    main()
