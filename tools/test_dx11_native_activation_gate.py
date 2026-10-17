#!/usr/bin/env python3
"""Static guard for DX11 conversion lane activation boundaries.

This intentionally does not enable the native draw path.  It protects the
conversion lane from treating dormant implementation evidence as runtime-ready
activation and catches incomplete state transitions.
"""

from pathlib import Path


STATE_FILES = (
    Path("docs/CONVERSION_LANE_STATE.json"),
    Path("docs/automation/runs/CONV-DX11-000001.json"),
)


def load_state_text():
    existing = [p for p in STATE_FILES if p.exists()]
    assert existing, "conversion state evidence is required"
    return "\n".join(p.read_text(encoding="utf-8") for p in existing)


def test_activation_marker_is_not_enabled_by_default():
    text = load_state_text()
    assert "native_draw_path_activation_changed\": true" not in text
    assert "runtime_validation\": \"PASSED" not in text


def test_activation_requires_runtime_gate_evidence():
    text = load_state_text()
    if "native_draw_path_activation_changed\": true" in text:
        assert "Quest 3" in text or "VDXR" in text
        assert "exact" in text.lower()


if __name__ == "__main__":
    test_activation_marker_is_not_enabled_by_default()
    test_activation_requires_runtime_gate_evidence()
    print("DX11 activation boundary static guard passed")
