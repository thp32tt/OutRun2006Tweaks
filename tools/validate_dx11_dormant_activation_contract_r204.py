#!/usr/bin/env python3
"""DX11 dormant activation contract guard.

Offline/static guard for the DX11 conversion lane.  It intentionally checks
source contracts only; it does not claim runtime validation.
"""

from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = {
        "runtime_validation": "UNTESTED",
        "backend": "DX11",
        "native_draw_path_activation": "disabled",
    }

    state = root / "docs" / "CONVERSION_LANE_STATE.json"
    if not state.exists():
        print("missing DX11 conversion state")
        return 1

    text = state.read_text(encoding="utf-8")
    missing = [f"{k}={v}" for k, v in required.items() if v not in text]
    if missing:
        print("contract mismatch: " + ", ".join(missing))
        return 1

    print("DX11 dormant activation contract: PASS")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
