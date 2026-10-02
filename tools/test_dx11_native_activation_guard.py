#!/usr/bin/env python3
"""Static DX11 conversion guard fixture.

This test artifact documents the invariant that offline conversion analysis must
not promote NativeDrawPath activation without runtime evidence. It is intended
for future CI/static gate wiring and intentionally performs no hardware probe.
"""

from __future__ import annotations


REQUIRED_STATIC_GUARD_FIELDS = (
    "NativeDrawPathActivationAllowed",
    "ActivationProof",
    "DiagnosticOnly",
)


def validate_activation_record(record: dict) -> None:
    """Reject records that claim activation without proof evidence."""
    missing = [key for key in REQUIRED_STATIC_GUARD_FIELDS if key not in record]
    if missing:
        raise AssertionError(f"missing activation guard fields: {missing}")

    if record["NativeDrawPathActivationAllowed"]:
        if not record["ActivationProof"]:
            raise AssertionError(
                "activation cannot be allowed without ActivationProof"
            )
        if record["DiagnosticOnly"]:
            raise AssertionError(
                "diagnostic-only records cannot activate native draw path"
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
