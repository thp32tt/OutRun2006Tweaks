#!/usr/bin/env python3
"""Static boundary checks for DXVK continuation evidence windows.

This verifies byte-window boundary invariants only. It does not infer runtime
or renderer semantics from disassembly bytes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceWindow:
    start_rva: int
    end_rva: int
    overlap_bytes: str

    def overlap_length(self) -> int:
        return len(self.overlap_bytes.split())

    def validate(self) -> None:
        bytes_ = self.overlap_bytes.split()
        assert self.end_rva > self.start_rva
        assert bytes_
        assert all(len(byte) == 2 for byte in bytes_)
        assert all(int(byte, 16) >= 0 for byte in bytes_)
        assert self.start_rva + self.overlap_length() <= self.end_rva

    def contains_continuation_overlap(self) -> bool:
        return self.overlap_length() > 0 and self.start_rva < self.end_rva


def test_continuation_window_boundary_is_valid() -> None:
    window = EvidenceWindow(
        start_rva=0x00182F7E,
        end_rva=0x00182FBE,
        overlap_bytes="66 0f 54 1d 20 91 61",
    )
    window.validate()
    assert window.contains_continuation_overlap()


def test_invalid_window_is_rejected() -> None:
    window = EvidenceWindow(
        start_rva=0x20,
        end_rva=0x10,
        overlap_bytes="66 0f",
    )
    try:
        window.validate()
    except AssertionError:
        return
    raise AssertionError("invalid continuation window was accepted")


if __name__ == "__main__":
    test_continuation_window_boundary_is_valid()
    test_invalid_window_is_rejected()
    print("DXVK continuation RVA boundary guard: PASS")
