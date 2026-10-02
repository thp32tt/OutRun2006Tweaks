#!/usr/bin/env python3
"""Regression checks for DXVK attestation contract validation.

These checks cover evidence-contract behavior only. They do not assert runtime
or Quest/VDXR readiness.
"""

from verify_dxvk_attestation_report_contract import verify


VALID = {
    "SchemaVersion": 1,
    "Status": "PASS",
    "DeviceCreationAttestationIdsValid": True,
    "DeviceCreationReattestationPassed": True,
    "RuntimeVersionMatchesPreflight": True,
}


def test_valid_report_passes():
    assert verify(VALID) == []


def test_duplicate_identity_failure_state_is_rejected():
    report = dict(VALID)
    report["DeviceCreationAttestationIdsValid"] = False
    assert "creation_attestation_ids_not_valid" in verify(report)


def test_known_bad_status_is_rejected():
    report = dict(VALID)
    report["Status"] = "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID"
    assert "invalid_status=DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID" in verify(report)
