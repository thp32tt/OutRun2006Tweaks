#!/usr/bin/env python3
"""Static contract checks for DXVK conversion evidence artifacts.

This test intentionally does not assert runtime behavior. It protects the
GitHub-only conversion lane from accidentally treating runtime-unverified
static evidence as semantic promotion.
"""

from pathlib import Path


REQUIRED_STATE_MARKERS = (
    '"runtime_validation": "UNTESTED"',
    '"lane": "DXVK"',
    '"github_only_development": true',
)


def test_dxvk_conversion_state_keeps_runtime_gate_closed():
    state = Path("docs/CONVERSION_LANE_STATE.json")
    assert state.exists(), "conversion lane state must exist"

    text = state.read_text(encoding="utf-8")
    for marker in REQUIRED_STATE_MARKERS:
        assert marker in text, f"missing DXVK conversion contract marker: {marker}"


def test_no_dx12_promotion_marker_in_conversion_state():
    state = Path("docs/CONVERSION_LANE_STATE.json")
    text = state.read_text(encoding="utf-8").lower()
    assert "promote_dx12" not in text
    assert "d3d9on12 active" not in text


if __name__ == "__main__":
    test_dxvk_conversion_state_keeps_runtime_gate_closed()
    test_no_dx12_promotion_marker_in_conversion_state()
    print("DXVK frontier contract checks passed")
