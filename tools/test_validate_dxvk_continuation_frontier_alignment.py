#!/usr/bin/env python3
"""Static contract checks for DXVK continuation frontier validators.

Keeps overlap/frontier validation evidence bounded to byte provenance. This
must not be interpreted as runtime or rendering validation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_dxvk_continuation_window",
        ROOT / "validate_dxvk_continuation_window.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_overlap_must_be_inside_declared_window():
    validator = load_validator()
    window = validator.validate_window(
        bytes.fromhex("66 0f 54 1d 20 91 61 aa"),
        0,
        7,
        "66 0f 54 1d 20 91 61",
    )
    assert window["matches"]
    assert window["window_contains_overlap"]


def test_partial_overlap_is_detected():
    validator = load_validator()
    window = validator.validate_window(
        bytes.fromhex("66 0f 54 1d 20 91"),
        0,
        6,
        "66 0f 54 1d 20 91 61",
    )
    errors = validator.validate_expected_frontier(window)
    assert "truncated_frontier_overlap" in errors


if __name__ == "__main__":
    test_overlap_must_be_inside_declared_window()
    test_partial_overlap_is_detected()
    print("DXVK_CONTINUATION_FRONTIER_ALIGNMENT_CONTRACT=PASS")
