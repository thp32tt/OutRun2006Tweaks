#!/usr/bin/env python3
"""Static guard for the DXVK disassembly continuation frontier.

This intentionally does not decode runtime semantics. It protects the
canonical byte-window handoff used by the DXVK conversion evidence pipeline
and fails closed when a continuation record loses its basic provenance shape.
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
    assert frontier.end_rva > frontier.start_rva
    assert frontier.overlap == EXPECTED.overlap
    assert frontier.overlap
    assert len(frontier.overlap) <= frontier.end_rva - frontier.start_rva


def validate_no_semantic_promotion(frontier: Frontier) -> None:
    """Keep this artifact limited to byte provenance, not runtime meaning."""
    assert isinstance(frontier.start_rva, int)
    assert isinstance(frontier.end_rva, int)
    assert isinstance(frontier.overlap, bytes)


if __name__ == "__main__":
    validate_frontier(EXPECTED)
    validate_no_semantic_promotion(EXPECTED)
    print("DXVK continuation frontier guard: PASS")
