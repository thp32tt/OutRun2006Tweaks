#!/usr/bin/env python3
from verify_dxvk_raw_window import validate_raw_window

VALID = {
    "runtime_validation": "UNTESTED",
    "provenance_start_rva": "0x00182F7E",
    "probe_end_rva": "0x00182FBE",
    "overlap_bytes": "66 0f 54 1d 20 91 61",
}


def test_raw_window_contract():
    assert validate_raw_window(VALID) == []


def test_runtime_claim_fails_closed():
    report = dict(VALID)
    report["runtime_validation"] = "PASS"
    assert "runtime_validation_must_remain_untested" in validate_raw_window(report)


def test_anchor_mismatch_fails_closed():
    report = dict(VALID)
    report["overlap_bytes"] = "90 90"
    assert "overlap_anchor_mismatch" in validate_raw_window(report)
