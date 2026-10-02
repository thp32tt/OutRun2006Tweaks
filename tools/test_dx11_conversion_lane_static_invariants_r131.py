#!/usr/bin/env python3
"""Static invariants for the DX11 conversion lane.

This offline check intentionally does not activate NativeDrawPath.  It verifies
that conversion tooling and branch-local guards keep activation disabled until
runtime evidence gates are satisfied.
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

    agents = ROOT / "AGENTS.md"
    require_text(
        agents,
        [
            "Keep NativeDrawPathActive disabled",
            "runtime UNTESTED",
        ],
    )

    print("DX11_CONVERSION_STATIC_INVARIANTS=PASS")
    print("NATIVE_DRAW_PATH_ACTIVATION=DISABLED")
    print("RUNTIME_VALIDATION=UNTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
