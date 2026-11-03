#!/usr/bin/env python3
"""Validate ordered DXVK disassembly frontier evidence windows.

This validator only checks evidence continuity metadata. It deliberately avoids
instruction semantics, runtime behavior, or backend activation claims.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Frontier:
    start_rva: int
    end_rva: int
    predecessor_end_rva: int
    overlap: bytes


def validate_chain(frontiers: list[Frontier]) -> None:
    if not frontiers:
        raise ValueError("empty frontier chain")

    for index, frontier in enumerate(frontiers):
        if frontier.end_rva <= frontier.start_rva:
            raise ValueError(f"invalid range at {index}")
        if not frontier.overlap:
            raise ValueError(f"missing overlap at {index}")
        if index and frontier.start_rva != frontiers[index - 1].end_rva:
            raise ValueError(f"gap between frontier {index - 1} and {index}")
        if frontier.predecessor_end_rva != frontier.start_rva:
            raise ValueError(f"predecessor mismatch at {index}")


def main() -> None:
    validate_chain(
        [
            Frontier(0x182F45, 0x182F7E, 0x182F45, bytes.fromhex("66 0f 54 1d 20 91 61")),
            Frontier(0x182F7E, 0x182FBE, 0x182F7E, bytes.fromhex("66 0f 54 1d 20 91 61")),
        ]
    )
    print("DXVK_FRONTIER_CHAIN_VALIDATOR=PASS")


if __name__ == "__main__":
    main()
