#!/usr/bin/env python3
"""Static DX11 conversion guard for dormant activation paths.

Checks that DX11 conversion work keeps native draw activation explicit and
prevents accidental promotion through configuration-only changes.
This is repository validation only; it does not claim runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = (ROOT / "OutRun2006Tweaks.ini").read_text(encoding="utf-8")
    state = (ROOT / "docs" / "CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")

    if '"lane": "DX11"' not in state:
        raise SystemExit("DX11 lane marker missing")

    forbidden_activation = [
        "NativeDrawPathActive=true",
        "EnableNativeDrawPath=true",
    ]
    found = [item for item in forbidden_activation if item in config]
    if found:
        raise SystemExit("DX11 dormant activation drift: " + ", ".join(found))

    if '"runtime_validation": "UNTESTED"' not in state:
        raise SystemExit("runtime validation marker drift")

    print("DX11 dormant activation guard R202: PASS")


if __name__ == "__main__":
    main()
