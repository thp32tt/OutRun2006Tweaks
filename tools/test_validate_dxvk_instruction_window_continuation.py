#!/usr/bin/env python3
"""Static guard for DXVK disassembly continuation windows.

This test intentionally does not decode semantics. It only protects the
canonical byte-overlap contract used when a disassembly capture ends inside
an x86 instruction and the next window must begin with the preserved overlap.
"""

EXPECTED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_continuation_window(previous_tail: bytes, next_window_head: bytes) -> None:
    if len(previous_tail) < len(EXPECTED_OVERLAP):
        raise AssertionError("previous capture tail is too short for mandatory overlap")
    if previous_tail[-len(EXPECTED_OVERLAP):] != EXPECTED_OVERLAP:
        raise AssertionError("previous capture does not end with canonical overlap")
    if next_window_head[: len(EXPECTED_OVERLAP)] != EXPECTED_OVERLAP:
        raise AssertionError("next capture does not preserve canonical overlap")


def test_canonical_f43_overlap_contract():
    sample = EXPECTED_OVERLAP + bytes.fromhex("90 90")
    validate_continuation_window(sample, sample)


if __name__ == "__main__":
    test_canonical_f43_overlap_contract()
    print("DXVK continuation overlap contract: PASS")
