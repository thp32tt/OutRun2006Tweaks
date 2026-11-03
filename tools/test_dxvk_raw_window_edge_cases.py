#!/usr/bin/env python3
"""Regression cases for DXVK raw-window provenance guards."""

from verify_dxvk_raw_window import validate_raw_window


BASELINE = {
    "runtime_validation": "UNTESTED",
    "provenance_start_rva": "0x00182F7E",
    "probe_end_rva": "0x00182FBE",
    "overlap_bytes": "66 0f 54 1d 20 91 61",
}


def test_whitespace_is_accepted_for_captured_hex():
    report = dict(BASELINE)
    report["overlap_bytes"] = "66   0F 54 1D 20 91 61"
    assert validate_raw_window(report) == []


def test_missing_runtime_marker_is_rejected():
    report = dict(BASELINE)
    del report["runtime_validation"]
    assert "runtime_validation_must_remain_untested" in validate_raw_window(report)


def test_probe_range_changes_are_rejected():
    report = dict(BASELINE)
    report["probe_end_rva"] = "0x00182FBF"
    assert "raw_window_end_mismatch" in validate_raw_window(report)
