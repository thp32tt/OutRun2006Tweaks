#!/usr/bin/env python3
"""Static guard for the DXVK disassembly continuation frontier.

This intentionally does not decode runtime semantics. It only protects the
canonical byte-window handoff used by the DXVK conversion evidence pipeline.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Frontier:
    start_rva: int
    end_rva: int
    overlap: bytes


EXPECTED = Frontier(
    start_rva=0x182F7E,
    end_rva=0x182FBE,
    overlap=bytes.fromhex("66 0f 54 1d 20 91 61"),
)


def validate_frontier(frontier: Frontier) -> None:
    assert frontier.start_rva == EXPECTED.start_rva
    assert frontier.end_rva == EXPECTED.end_rva
    assert frontier.overlap == EXPECTED.overlap
    assert len(frontier.overlap) == 7


if __name__ == "__main__":
    validate_frontier(EXPECTED)
    print("DXVK continuation frontier guard: PASS")
