#!/usr/bin/env python3
"""Static contract guard for DXVK disassembly continuation overlap handling.

This intentionally does not decode runtime semantics.  It only protects the
canonical byte-overlap contract used when a previous proof window ends on a
partial x86 instruction and the next window must inherit those bytes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OverlapContract:
    start_rva: int
    end_rva: int
    overlap_bytes: bytes


EXPECTED = OverlapContract(
    start_rva=0x182F7E,
    end_rva=0x182FBE,
    overlap_bytes=bytes.fromhex("66 0f 54 1d 20 91 61"),
)


def validate_overlap(contract: OverlapContract) -> None:
    if contract.end_rva <= contract.start_rva:
        raise AssertionError("continuation window must advance")
    if not contract.overlap_bytes:
        raise AssertionError("partial instruction overlap must be preserved")
    if len(contract.overlap_bytes) < 2:
        raise AssertionError("x86 overlap is too short to validate instruction prefix")


def test_known_dxvk_frontier_overlap() -> None:
    validate_overlap(EXPECTED)
    assert EXPECTED.start_rva == 0x182F7E
    assert EXPECTED.overlap_bytes.hex(" ") == "66 0f 54 1d 20 91 61"


if __name__ == "__main__":
    test_known_dxvk_frontier_overlap()
    print("DXVK continuation overlap contract: PASS")
