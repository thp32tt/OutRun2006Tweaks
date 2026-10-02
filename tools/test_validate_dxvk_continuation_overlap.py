#!/usr/bin/env python3
"""Regression checks for DXVK continuation overlap validation."""

from validate_dxvk_continuation_overlap import validate_window


def test_accepts_exact_overlap_prefix():
    ok, message = validate_window(
        "66 0f 54 1d 20 91 61",
        "66 0f 54 1d 20 91 61 90 90",
    )
    assert ok
    assert message == "overlap preserved"


def test_rejects_short_window():
    ok, message = validate_window(
        "66 0f 54 1d 20 91 61",
        "66 0f 54",
    )
    assert not ok
    assert message == "continuation window shorter than required overlap"


def test_rejects_changed_prefix_byte():
    ok, message = validate_window(
        "66 0f 54 1d 20 91 61",
        "66 0f 54 1d 20 91 62",
    )
    assert not ok
    assert message == "continuation overlap mismatch"
