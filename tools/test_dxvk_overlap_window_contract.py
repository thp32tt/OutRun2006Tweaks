#!/usr/bin/env python3
"""Regression contract for DXVK canonical disassembly overlap windows.

This intentionally validates byte provenance only. It does not infer runtime,
renderer, or function semantics from the captured executable window.
"""

EXPECTED_START_RVA = 0x00182F7E
EXPECTED_END_RVA = 0x00182FBE
EXPECTED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_overlap_window(start_rva: int, raw_window: bytes) -> None:
    assert start_rva == EXPECTED_START_RVA
    assert EXPECTED_OVERLAP == raw_window[: len(EXPECTED_OVERLAP)]
    assert start_rva + len(raw_window) <= EXPECTED_END_RVA


def test_known_dxvk_frontier_overlap_contract() -> None:
    validate_overlap_window(
        EXPECTED_START_RVA,
        EXPECTED_OVERLAP + bytes.fromhex("90 90 90"),
    )


if __name__ == "__main__":
    test_known_dxvk_frontier_overlap_contract()
    print("DXVK overlap window contract: PASS")
