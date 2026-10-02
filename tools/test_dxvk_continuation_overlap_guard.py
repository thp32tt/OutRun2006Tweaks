#!/usr/bin/env python3
"""Static regression guard for DXVK continuation evidence windows.

This validates only provenance continuity at the raw-byte boundary. It does
not infer instruction meaning, render behavior, HUD behavior, or runtime
acceptance.

The guard rejects accidental promotion of a continuation overlap into a
complete decoded instruction and checks boundary identity fields together.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OverlapRecord:
    start_rva: str
    end_rva: str
    bytes_hex: str
    predecessor_overlap: bool
    decode_complete: bool
    predecessor_end_rva: str


EXPECTED_START = "0x00182F7E"
EXPECTED_END = "0x00182FBE"
EXPECTED_PREDECESSOR_END = "0x00182F7E"
EXPECTED_OVERLAP = "66 0f 54 1d 20 91 61"


def validate_overlap_record(record: OverlapRecord) -> None:
    assert record.start_rva == EXPECTED_START
    assert record.end_rva == EXPECTED_END
    assert record.predecessor_end_rva == EXPECTED_PREDECESSOR_END
    assert bytes.fromhex(record.bytes_hex) == bytes.fromhex(EXPECTED_OVERLAP)
    assert record.predecessor_overlap is True
    assert record.decode_complete is False


def validate_frontier_transition(previous_end_rva: str, next_start_rva: str) -> None:
    """Require a continuation window to start exactly at the previous edge."""
    assert previous_end_rva == next_start_rva


def validate_partial_instruction_requires_overlap(decode_complete: bool, overlap_bytes: str) -> None:
    """Fail closed if partial instruction evidence is promoted without bytes."""
    if not decode_complete:
        assert len(bytes.fromhex(overlap_bytes)) > 0


def test_dxvk_continuation_overlap_guard() -> None:
    validate_overlap_record(
        OverlapRecord(
            start_rva=EXPECTED_START,
            end_rva=EXPECTED_END,
            bytes_hex=EXPECTED_OVERLAP,
            predecessor_overlap=True,
            decode_complete=False,
            predecessor_end_rva=EXPECTED_PREDECESSOR_END,
        )
    )


def test_dxvk_continuation_frontier_edge_alignment() -> None:
    validate_frontier_transition(
        EXPECTED_PREDECESSOR_END,
        EXPECTED_START,
    )


def test_dxvk_partial_decode_stays_unresolved() -> None:
    validate_partial_instruction_requires_overlap(False, EXPECTED_OVERLAP)


def test_dxvk_partial_decode_rejects_missing_overlap_bytes() -> None:
    try:
        validate_partial_instruction_requires_overlap(False, "")
    except AssertionError:
        return
    raise AssertionError("missing overlap evidence was accepted")


if __name__ == "__main__":
    test_dxvk_continuation_overlap_guard()
    test_dxvk_continuation_frontier_edge_alignment()
    test_dxvk_partial_decode_stays_unresolved()
    test_dxvk_partial_decode_rejects_missing_overlap_bytes()
    print("DXVK_CONTINUATION_OVERLAP_GUARD=PASS")
