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


if __name__ == "__main__":
    validate_activation_record(
        {
            "NativeDrawPathActivationAllowed": False,
            "ActivationProof": False,
            "DiagnosticOnly": True,
            "BackendLane": "DX11",
        }
    )
    print("DX11 activation record schema OK")
