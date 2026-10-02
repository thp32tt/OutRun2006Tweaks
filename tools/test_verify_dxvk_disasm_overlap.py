#!/usr/bin/env python3
"""Regression checks for DXVK disassembly overlap validation."""

from verify_dxvk_disasm_overlap import normalize_hex_bytes, validate_overlap


def test_exact_overlap_passes() -> None:
    overlap = normalize_hex_bytes("66 0f 54 1d")
    assert validate_overlap(
        normalize_hex_bytes("aa bb 66 0f 54 1d"),
        normalize_hex_bytes("66 0f 54 1d 20 91"),
        overlap,
    )


def test_wrong_overlap_fails() -> None:
    overlap = normalize_hex_bytes("66 0f 54 1d")
    assert not validate_overlap(
        normalize_hex_bytes("aa bb 66 0f 55 1d"),
        normalize_hex_bytes("66 0f 54 1d 20 91"),
        overlap,
    )


if __name__ == "__main__":
    test_exact_overlap_passes()
    test_wrong_overlap_fails()
    print("DXVK disassembly overlap regression: PASS")
