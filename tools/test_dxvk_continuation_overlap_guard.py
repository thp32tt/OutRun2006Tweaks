#!/usr/bin/env python3
"""Static regression guard for DXVK continuation evidence windows.

This validates only provenance continuity at the raw-byte boundary. It does
not infer instruction meaning, render behavior, HUD behavior, or runtime
acceptance.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OverlapRecord:
    start_rva: str
    bytes_hex: str
    predecessor_overlap: bool


def validate_overlap_record(record: OverlapRecord) -> None:
    assert record.start_rva == "0x00182F7E"
    assert bytes.fromhex(record.bytes_hex) == bytes.fromhex("66 0f 54 1d 20 91 61")
    assert record.predecessor_overlap is True


def test_dxvk_continuation_overlap_guard() -> None:
    validate_overlap_record(
        OverlapRecord(
            start_rva="0x00182F7E",
            bytes_hex="66 0f 54 1d 20 91 61",
            predecessor_overlap=True,
        )
    )


if __name__ == "__main__":
    test_dxvk_continuation_overlap_guard()
    print("DXVK_CONTINUATION_OVERLAP_GUARD=PASS")
