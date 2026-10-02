#!/usr/bin/env python3
"""Regression tests for DXVK continuation-window evidence validation."""

from Validate-DXVK-ContinuationWindow import validate_window


def test_exact_frontier_accepts_canonical_window():
    record = {
        "lane": "DXVK",
        "follow_on_frontier": {
            "provenance_status": "EXACT_EXE_182F7E_TO_182FBE_PROVENANCE_CAPTURED",
            "overlap_bytes": "66 0f 54 1d 20 91 61",
            "provenance_start_rva": "0x00182F7E",
            "probe_end_rva": "0x00182FBE",
        },
    }
    assert validate_window(record) == []


def test_frontier_rejects_changed_overlap():
    record = {
        "lane": "DXVK",
        "follow_on_frontier": {
            "provenance_status": "EXACT_EXE_182F7E_TO_182FBE_PROVENANCE_CAPTURED",
            "overlap_bytes": "90 90",
            "provenance_start_rva": "0x00182F7E",
            "probe_end_rva": "0x00182FBE",
        },
    }
    assert "mandatory overlap bytes do not match" in validate_window(record)
