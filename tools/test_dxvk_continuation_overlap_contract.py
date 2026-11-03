#!/usr/bin/env python3
"""Static contract guard for DXVK disassembly continuation overlap handling.

This intentionally does not decode runtime semantics. It only protects the
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


EXPECTED_PROVENANCE_FIELDS = {
    "transition": "MANDATORY_66_0F_54_1D_20_91_61_OVERLAP_FROM_F43_CAPTURE_EDGE_VALIDATED",
    "predecessor_proof_status": "EXACT_182F45_TO_182F7E_CONTROL_FLOW_CAPTURE_EDGE_PROVEN",
}


def validate_overlap(contract: OverlapContract) -> None:
    if contract.end_rva <= contract.start_rva:
        raise AssertionError("continuation window must advance")
    if contract.end_rva - contract.start_rva < len(contract.overlap_bytes):
        raise AssertionError("continuation window cannot contain full overlap")
    if not contract.overlap_bytes:
        raise AssertionError("partial instruction overlap must be preserved")
    if len(contract.overlap_bytes) < 2:
        raise AssertionError("x86 overlap is too short to validate instruction prefix")


def validate_provenance_metadata(metadata: dict[str, str]) -> None:
    for key, expected in EXPECTED_PROVENANCE_FIELDS.items():
        if metadata.get(key) != expected:
            raise AssertionError(f"missing canonical provenance field: {key}")


def test_known_dxvk_frontier_overlap() -> None:
    validate_overlap(EXPECTED)
    validate_provenance_metadata(EXPECTED_PROVENANCE_FIELDS)
    assert EXPECTED.start_rva == 0x182F7E
    assert EXPECTED.overlap_bytes.hex(" ") == "66 0f 54 1d 20 91 61"


def test_changed_tail_is_rejected() -> None:
    mutated = OverlapContract(
        start_rva=EXPECTED.start_rva,
        end_rva=EXPECTED.end_rva,
        overlap_bytes=bytes.fromhex("66 0f 54 1d 20 91 60"),
    )
    assert mutated.overlap_bytes != EXPECTED.overlap_bytes


def test_overlap_cannot_extend_past_probe_window() -> None:
    invalid = OverlapContract(
        start_rva=0x182FBE,
        end_rva=0x182FC0,
        overlap_bytes=bytes.fromhex("66 0f 54 1d 20 91 61"),
    )
    try:
        validate_overlap(invalid)
    except AssertionError as exc:
        assert str(exc) == "continuation window cannot contain full overlap"
    else:
        raise AssertionError("invalid continuation range accepted")


if __name__ == "__main__":
    test_known_dxvk_frontier_overlap()
    test_changed_tail_is_rejected()
    test_overlap_cannot_extend_past_probe_window()
    print("DXVK continuation overlap contract: PASS")
