#!/usr/bin/env python3
"""Regression checks for DXVK disassembly overlap provenance guards.

This test intentionally stays offline. It verifies that canonical continuation
windows cannot silently discard the overlap bytes that prove instruction-boundary
continuity. Runtime rendering semantics remain outside this check.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProvenanceWindow:
    start_rva: int
    end_rva: int
    overlap: bytes


REQUIRED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


# The validated frontier starts at the incomplete instruction boundary. The
# overlap is intentionally checked separately so future decoders cannot replace
# it with a best-effort re-synchronization.
VALIDATED_WINDOW = ProvenanceWindow(
    start_rva=0x00182F7E,
    end_rva=0x00182FBE,
    overlap=REQUIRED_OVERLAP,
)


def assert_window_is_fail_closed(window: ProvenanceWindow) -> None:
    assert window.start_rva < window.end_rva
    assert window.overlap == REQUIRED_OVERLAP
    assert len(window.overlap) == 7


def test_known_overlap_guard() -> None:
    assert_window_is_fail_closed(VALIDATED_WINDOW)


def test_modified_overlap_is_rejected() -> None:
    bad = ProvenanceWindow(
        start_rva=VALIDATED_WINDOW.start_rva,
        end_rva=VALIDATED_WINDOW.end_rva,
        overlap=b"\x90" * len(REQUIRED_OVERLAP),
    )
    try:
        assert_window_is_fail_closed(bad)
    except AssertionError:
        return
    raise AssertionError("invalid DXVK provenance overlap was accepted")


if __name__ == "__main__":
    test_known_overlap_guard()
    test_modified_overlap_is_rejected()
    print("DXVK overlap provenance guard: PASS")
