#!/usr/bin/env python3
"""Static guard for DX11 conversion lane activation boundaries.

This intentionally does not enable the native draw path.  It protects the
conversion lane from accidentally treating dormant implementation evidence as
runtime-ready activation.
"""

from pathlib import Path


def test_activation_marker_is_not_enabled_by_default():
    state_files = [
        Path("docs/CONVERSION_LANE_STATE.json"),
        Path("docs/automation/runs/CONV-DX11-000001.json"),
    ]

    existing = [p for p in state_files if p.exists()]
    assert existing, "conversion state evidence is required"

    text = "\n".join(p.read_text(encoding="utf-8") for p in existing)
    assert "native_draw_path_activation_changed\": true" not in text
    assert "runtime_validation\": \"PASSED" not in text


if __name__ == "__main__":
    test_activation_marker_is_not_enabled_by_default()
    print("DX11 activation boundary static guard passed")
