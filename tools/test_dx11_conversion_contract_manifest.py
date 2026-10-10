#!/usr/bin/env python3
"""Static DX11 conversion lane contract smoke helper.

This intentionally does not enable NativeDrawPathActive.  It provides a small
repository-side regression check for conversion branches by verifying that the
branch keeps the conversion safety boundary explicit before runtime evidence is
available.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    if not state.exists():
        raise SystemExit("missing DX11 conversion lane state")

    text = state.read_text(encoding="utf-8")
    required = (
        '"lane": "DX11"',
        '"runtime_validation": "UNTESTED"',
        '"native_draw_path_activation_changed": false',
    )

    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit("DX11 conversion contract drift: " + ", ".join(missing))

    print("DX11 conversion contract manifest: PASS")


if __name__ == "__main__":
    main()
