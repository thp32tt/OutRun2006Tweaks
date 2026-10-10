#!/usr/bin/env python3
"""Validate DX11 activation records without requiring runtime hardware.

The conversion lane may inspect dormant activation candidates offline, but an
activation record must keep evidence requirements explicit. This validator is
intentionally platform independent and only checks the static contract.
"""

from __future__ import annotations

REQUIRED_FIELDS = {
    "NativeDrawPathActivationAllowed",
    "ActivationProof",
    "DiagnosticOnly",
    "BackendLane",
}


def validate_activation_record(record: dict) -> None:
    missing = sorted(REQUIRED_FIELDS - record.keys())
    if missing:
        raise AssertionError(f"missing DX11 activation fields: {missing}")

    if record["BackendLane"] != "DX11":
        raise AssertionError("record must belong to DX11 lane")

    if bool(record["NativeDrawPathActivationAllowed"]):
        if not bool(record["ActivationProof"]):
            raise AssertionError("activation requires proof evidence")
        if bool(record["DiagnosticOnly"]):
            raise AssertionError("diagnostic records cannot activate")


def _expect_rejection(record: dict) -> None:
    try:
        validate_activation_record(record)
    except AssertionError:
        return
    raise AssertionError("invalid activation record was accepted")


def run_contract_smoke_tests() -> None:
    validate_activation_record(
        {
            "NativeDrawPathActivationAllowed": False,
            "ActivationProof": False,
            "DiagnosticOnly": True,
            "BackendLane": "DX11",
        }
    )

    _expect_rejection(
        {
            "NativeDrawPathActivationAllowed": True,
            "ActivationProof": False,
            "DiagnosticOnly": False,
            "BackendLane": "DX11",
        }
    )

    _expect_rejection(
        {
            "NativeDrawPathActivationAllowed": True,
            "ActivationProof": True,
            "DiagnosticOnly": True,
            "BackendLane": "DX11",
        }
    )

    _expect_rejection(
        {
            "NativeDrawPathActivationAllowed": False,
            "ActivationProof": False,
            "DiagnosticOnly": True,
            "BackendLane": "DXVK",
        }
    )


if __name__ == "__main__":
    run_contract_smoke_tests()
    print("DX11 activation record schema OK")
