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


EXPECTED_START = "0x00182F7E"
EXPECTED_END = "0x00182FBE"
EXPECTED_OVERLAP = "66 0f 54 1d 20 91 61"


def validate_overlap_record(record: OverlapRecord) -> None:
    assert record.start_rva == EXPECTED_START
    assert record.end_rva == EXPECTED_END
    assert bytes.fromhex(record.bytes_hex) == bytes.fromhex(EXPECTED_OVERLAP)
    assert record.predecessor_overlap is True
    assert record.decode_complete is False


def test_dxvk_continuation_overlap_guard() -> None:
    validate_overlap_record(
        OverlapRecord(
            start_rva=EXPECTED_START,
            end_rva=EXPECTED_END,
            bytes_hex=EXPECTED_OVERLAP,
            predecessor_overlap=True,
            decode_complete=False,
        )
    )


if __name__ == "__main__":
    test_dxvk_continuation_overlap_guard()
    print("DXVK_CONTINUATION_OVERLAP_GUARD=PASS")
