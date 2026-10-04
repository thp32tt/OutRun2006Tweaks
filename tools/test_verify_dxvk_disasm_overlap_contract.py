#!/usr/bin/env python3
"""Regression checks for DXVK continuation overlap evidence validation."""

from verify_dxvk_disasm_overlap_contract import validate_overlap_contract


VALID = {
    "runtime_validation": "UNTESTED",
    "predecessor_exact": True,
    "overlap_bytes": "66 0f 54 1d 20 91 61",
}


def test_valid_overlap_contract():
    assert validate_overlap_contract(VALID) == []


def test_runtime_claim_is_rejected():
    report = dict(VALID)
    report["runtime_validation"] = "PASS"
    assert "runtime_claim_must_remain_untested" in validate_overlap_contract(report)


def test_overlap_mismatch_is_rejected():
    report = dict(VALID)
    report["overlap_bytes"] = "90 90"
    assert "mandatory_overlap_bytes_mismatch" in validate_overlap_contract(report)
