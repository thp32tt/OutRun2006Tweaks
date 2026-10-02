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

    def validate(self) -> None:
        assert self.end_rva > self.start_rva
        assert len(self.overlap_bytes.split()) > 0
        assert all(len(byte) == 2 for byte in self.overlap_bytes.split())
        assert all(int(byte, 16) >= 0 for byte in self.overlap_bytes.split())


def test_continuation_window_boundary_is_valid() -> None:
    window = EvidenceWindow(
        start_rva=0x00182F7E,
        end_rva=0x00182FBE,
        overlap_bytes="66 0f 54 1d 20 91 61",
    )
    window.validate()
    assert window.start_rva + len(window.overlap_bytes.split()) <= window.end_rva


if __name__ == "__main__":
    test_continuation_window_boundary_is_valid()
    print("DXVK continuation RVA boundary guard: PASS")
