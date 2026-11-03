"""Static regression checks for DXVK disassembly continuation overlap handling.

This test is intentionally independent of runtime hardware. It protects the evidence
contract that a continuation window beginning on an already-proven instruction edge
must preserve the predecessor overlap bytes before decoding the new window.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuationWindow:
    start_rva: int
    probe_end_rva: int
    overlap_hex: str


def validate_overlap(window: ContinuationWindow, predecessor_end_rva: int, overlap_hex: str) -> bool:
    """Fail closed when a continuation capture loses its predecessor bytes."""
    if window.start_rva != predecessor_end_rva:
        return False
    if not window.overlap_hex:
        return False
    return window.overlap_hex.lower().replace(" ", "") == overlap_hex.lower().replace(" ", "")


def test_182f7e_overlap_contract():
    window = ContinuationWindow(
        start_rva=0x00182F7E,
        probe_end_rva=0x00182FBE,
        overlap_hex="66 0f 54 1d 20 91 61",
    )
    assert validate_overlap(
        window,
        predecessor_end_rva=0x00182F7E,
        overlap_hex="66 0f 54 1d 20 91 61",
    )


def test_rejects_missing_overlap():
    window = ContinuationWindow(
        start_rva=0x00182F7E,
        probe_end_rva=0x00182FBE,
        overlap_hex="",
    )
    assert not validate_overlap(window, 0x00182F7E, "66 0f 54 1d 20 91 61")
