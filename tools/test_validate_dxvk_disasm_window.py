#!/usr/bin/env python3
"""Regression checks for validate_dxvk_disasm_window."""

from validate_dxvk_disasm_window import validate_overlap


def test_valid_overlap():
    assert validate_overlap("aa bb cc dd", "cc dd ee ff", 2)


def test_rejects_gap():
    assert not validate_overlap("aa bb cc dd", "cc ee ff", 2)


def test_rejects_invalid_overlap_size():
    try:
        validate_overlap("aa", "aa", 0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    test_valid_overlap()
    test_rejects_gap()
    test_rejects_invalid_overlap_size()
    print("DXVK_DISASM_WINDOW_TEST=PASS")
