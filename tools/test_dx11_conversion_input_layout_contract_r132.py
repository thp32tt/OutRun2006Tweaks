#!/usr/bin/env python3
"""Static contract check for the DX11 conversion input-layout lane.

This check does not enable native drawing. It guards the conversion boundary by
requiring explicit evidence markers before future activation work can proceed.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require_text(path: Path, needles: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"missing {path}: {missing}")


def main() -> int:
    state = ROOT / "docs" / "CONVERSION_LANE_STATE.json"
    if not state.exists():
        raise SystemExit("missing conversion lane state")

    require_text(
        state,
        [
            '"lane": "DX11"',
            '"runtime_validation": "UNTESTED"',
            '"native_draw_path_activation_changed": false',
        ],
    )

    require_text(
        ROOT / "AGENTS.md",
        [
            "DX11 Native is the primary implementation/performance lane",
            "Keep NativeDrawPathActive disabled",
        ],
    )

    print("DX11_INPUT_LAYOUT_STATIC_CONTRACT=PASS")
    print("NATIVE_DRAW_PATH_ACTIVATION=DISABLED")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
