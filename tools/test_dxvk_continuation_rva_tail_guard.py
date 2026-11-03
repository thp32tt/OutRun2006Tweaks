#!/usr/bin/env python3
"""Static regression guard for DXVK continuation disassembly windows.

This intentionally does not decode instructions.  It protects the evidence
contract that a continuation probe must preserve the first bytes of the next
window instead of silently truncating an overlap boundary.
"""

EXPECTED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_overlap(prefix: bytes, overlap: bytes) -> None:
    if not prefix:
        raise AssertionError("empty continuation prefix is invalid")
    if overlap != EXPECTED_OVERLAP:
        raise AssertionError("continuation overlap bytes changed")
    if not prefix.endswith(overlap):
        raise AssertionError("continuation prefix does not preserve overlap")


def test_expected_boundary() -> None:
    validate_overlap(b"\x90" + EXPECTED_OVERLAP, EXPECTED_OVERLAP)


def test_rejects_missing_tail() -> None:
    try:
        validate_overlap(b"\x90\x90", EXPECTED_OVERLAP)
    except AssertionError:
        return
    raise AssertionError("missing overlap must fail closed")


if __name__ == "__main__":
    test_expected_boundary()
    test_rejects_missing_tail()
    print("DXVK continuation tail boundary guard: PASS")
