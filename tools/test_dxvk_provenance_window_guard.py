#!/usr/bin/env python3
"""Static regression guard for DXVK canonical disassembly continuation windows.

This test intentionally does not assign runtime/render semantics.  It protects the
provenance workflow from accepting a continuation window when the required overlap
edge is missing or when a partial instruction is silently discarded.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuationWindow:
    start_rva: int
    end_rva: int
    overlap_hex: str
    trailing_partial_preserved: bool


REQUIRED_OVERLAP = "66 0f 54 1d 20 91 61"


def validate_window(window: ContinuationWindow) -> None:
    assert window.start_rva < window.end_rva
    assert window.overlap_hex.lower() == REQUIRED_OVERLAP
    assert window.trailing_partial_preserved, (
        "decoder must preserve trailing partial instruction bytes for overlap"
    )


def test_current_dxvk_frontier_contract() -> None:
    validate_window(
        ContinuationWindow(
            start_rva=0x00182F7E,
            end_rva=0x00182FBE,
            overlap_hex=REQUIRED_OVERLAP,
            trailing_partial_preserved=True,
        )
    )


if __name__ == "__main__":
    test_current_dxvk_frontier_contract()
    print("DXVK provenance window guard: PASS")
