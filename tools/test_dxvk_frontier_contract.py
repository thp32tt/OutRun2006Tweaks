#!/usr/bin/env python3
"""Static regression checks for DXVK disassembly frontier contracts.

This test intentionally validates only repository-side evidence contracts.
It does not promote disassembly bytes into runtime semantics.
"""

from pathlib import Path


REQUIRED_MARKERS = (
    "EXACT_EXE_",
    "runtime_validation",
    "UNTESTED",
)


def test_conversion_state_keeps_runtime_unpromoted() -> None:
    state = Path("docs/CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        assert marker in state, f"missing DXVK evidence marker: {marker}"


def test_no_local_truth_override_in_lane_state() -> None:
    state = Path("docs/CONVERSION_LANE_STATE.json").read_text(encoding="utf-8")
    assert '"github_only_development": true' in state
    assert '"local_development_pc_required": false' in state


if __name__ == "__main__":
    test_conversion_state_keeps_runtime_unpromoted()
    test_no_local_truth_override_in_lane_state()
    print("DXVK frontier contract tests passed")
