#!/usr/bin/env python3
"""Static contract checks for DXVK conversion evidence artifacts.

This test intentionally does not assert runtime behavior. It protects the
GitHub-only conversion lane from accidentally treating runtime-unverified
static evidence as semantic promotion.
"""

import json
from pathlib import Path


REQUIRED_STATE_MARKERS = (
    '"runtime_validation": "UNTESTED"',
    '"lane": "DXVK"',
    '"github_only_development": true',
)


def load_state():
    state = Path("docs/CONVERSION_LANE_STATE.json")
    assert state.exists(), "conversion lane state must exist"
    return json.loads(state.read_text(encoding="utf-8"))


def test_dxvk_conversion_state_keeps_runtime_gate_closed():
    state = Path("docs/CONVERSION_LANE_STATE.json")
    text = state.read_text(encoding="utf-8")
    for marker in REQUIRED_STATE_MARKERS:
        assert marker in text, f"missing DXVK conversion contract marker: {marker}"


def test_no_dx12_promotion_marker_in_conversion_state():
    text = Path("docs/CONVERSION_LANE_STATE.json").read_text(encoding="utf-8").lower()
    assert "promote_dx12" not in text
    assert "d3d9on12 active" not in text


def test_exact_frontier_evidence_remains_static_only():
    state = load_state()
    evidence = state["latest_static_evidence"]
    frontier = state["follow_on_frontier"]

    assert evidence["static_exe_analysis_status"] == "SUCCESS"
    assert evidence["runtime_validation"] == "UNTESTED"
    assert frontier["predecessor_exact"] is True
    assert frontier["runtime_validation"] == "UNTESTED"
    assert frontier["overlap_bytes"]


if __name__ == "__main__":
    test_dxvk_conversion_state_keeps_runtime_gate_closed()
    test_no_dx12_promotion_marker_in_conversion_state()
    test_exact_frontier_evidence_remains_static_only()
    print("DXVK frontier contract checks passed")
