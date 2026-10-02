#!/usr/bin/env python3
"""Validate DXVK raw disassembly continuation metadata.

This guard intentionally validates only evidence transport invariants. It does
not infer render, HUD, or runtime semantics from raw bytes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    start_rva: int
    end_rva: int
    instruction_count: int


def validate_window(window: Window) -> None:
    if window.start_rva < 0:
        raise AssertionError("RVA must be non-negative")
    if window.end_rva <= window.start_rva:
        raise AssertionError("window must have forward progress")
    if window.instruction_count <= 0:
        raise AssertionError("validated window requires instructions")


def test_follow_on_frontier_window() -> None:
    validate_window(Window(0x182F7E, 0x182FBE, 13))


if __name__ == "__main__":
    test_follow_on_frontier_window()
    print("DXVK continuation window metadata: PASS")
