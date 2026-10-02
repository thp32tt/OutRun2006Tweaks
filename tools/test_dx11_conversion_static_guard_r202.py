#!/usr/bin/env python3
"""DX11 conversion static guard R202.

Validates that the DX11 conversion lane keeps activation gates explicit while
native draw routing remains disabled. This is repository-only evidence and does
not claim Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    ini = (ROOT / "OutRun2006Tweaks.ini").read_text(encoding="utf-8")

    required_state = [
        '"lane": "DX11"',
        '"runtime_validation": "UNTESTED"',
        '"native_draw_path_activation_changed": false',
    ]
    missing = [item for item in required_state if item not in state]
    if missing:
        raise SystemExit("DX11 R202 state contract missing: " + ", ".join(missing))

    if "NativeDrawPathActive" in ini and "false" not in ini:
        raise SystemExit("DX11 R202 activation guard requires explicit disabled state")

    print("DX11 conversion static guard R202: PASS")


if __name__ == "__main__":
    main()
