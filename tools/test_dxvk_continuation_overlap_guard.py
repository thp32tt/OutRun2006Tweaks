#!/usr/bin/env python3
"""Static regression guard for DXVK continuation evidence windows."""

OVERLAP_RVA = "0x00182F7E"
OVERLAP_BYTES = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_overlap_record(record: dict) -> None:
    assert record["start_rva"] == OVERLAP_RVA
    assert bytes.fromhex(record["bytes"]) == OVERLAP_BYTES
    assert record["predecessor_overlap"] is True


def test_dxvk_continuation_overlap_guard() -> None:
    validate_overlap_record(
        {
            "start_rva": "0x00182F7E",
            "bytes": "66 0f 54 1d 20 91 61",
            "predecessor_overlap": True,
        }
    )


if __name__ == "__main__":
    test_dxvk_continuation_overlap_guard()
    print("DXVK_CONTINUATION_OVERLAP_GUARD=PASS")
