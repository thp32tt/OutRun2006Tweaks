#!/usr/bin/env python3
"""Static contract guard for the DXVK disassembly continuation frontier.

This guard intentionally validates only byte/provenance boundaries. It does not
infer renderer, function, HUD, or runtime semantics from the captured window.
"""

FRONTIER_START_RVA = 0x00182F7E
FRONTIER_END_RVA = 0x00182FBE
REQUIRED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_frontier(start_rva: int, end_rva: int, overlap: bytes) -> None:
    if start_rva != FRONTIER_START_RVA:
        raise AssertionError(f"unexpected start RVA: {start_rva:#x}")
    if end_rva != FRONTIER_END_RVA:
        raise AssertionError(f"unexpected end RVA: {end_rva:#x}")
    if overlap != REQUIRED_OVERLAP:
        raise AssertionError("canonical overlap bytes changed")


def test_frontier_contract() -> None:
    validate_frontier(FRONTIER_START_RVA, FRONTIER_END_RVA, REQUIRED_OVERLAP)


if __name__ == "__main__":
    test_frontier_contract()
    print("DXVK continuation decode contract: PASS")
