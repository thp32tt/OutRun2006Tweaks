#!/usr/bin/env python3
"""Regression tests for the DXVK session report static validator."""

from validate_dxvk_session_report import validate


def test_accepts_valid_attestation_sequence():
    report = {
        "SchemaVersion": 1,
        "Status": "OK",
        "DeviceCreationAttestationIds": [1, 2, 3],
        "DeviceCreationAttestationIdsValid": True,
        "RuntimeVersionMatchesPreflight": True,
    }
    assert validate(report) == []


def test_rejects_replayed_attestation_sequence():
    report = {
        "SchemaVersion": 1,
        "Status": "OK",
        "DeviceCreationAttestationIds": [7, 7],
        "DeviceCreationAttestationIdsValid": True,
        "RuntimeVersionMatchesPreflight": True,
    }
    assert "duplicate device creation attestation id" in validate(report)


def test_rejects_fail_closed_contradiction():
    report = {
        "SchemaVersion": 1,
        "Status": "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID",
        "DeviceCreationAttestationIds": [9],
        "DeviceCreationAttestationIdsValid": True,
        "RuntimeVersionMatchesPreflight": True,
    }
    assert "fail-closed status contradicts valid attestation ids" in validate(report)
