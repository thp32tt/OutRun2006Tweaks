#!/usr/bin/env python3
"""Static DX11 conversion guard fixture.

This validates the activation boundary used by the DX11 conversion lane.
It intentionally does not require Windows, a GPU, or runtime evidence.
"""

from __future__ import annotations


REQUIRED_STATIC_GUARD_FIELDS = (
    "NativeDrawPathActivationAllowed",
    "ActivationProof",
    "DiagnosticOnly",
)



def validate_activation_record(record: dict) -> None:
    """Reject records that claim activation without complete proof evidence."""
    missing = [key for key in REQUIRED_STATIC_GUARD_FIELDS if key not in record]
    if missing:
        raise AssertionError(f"missing activation guard fields: {missing}")

    allowed = bool(record["NativeDrawPathActivationAllowed"])
    proof = bool(record["ActivationProof"])
    diagnostic = bool(record["DiagnosticOnly"])

    if allowed and (not proof or diagnostic):
        raise AssertionError(
            "native draw path activation requires proof and a non-diagnostic record"
        )


if __name__ == "__main__":
    validate_activation_record(
        {
            "NativeDrawPathActivationAllowed": False,
            "ActivationProof": False,
            "DiagnosticOnly": True,
        }
    )
    print("DX11 native activation guard fixture: PASS")
