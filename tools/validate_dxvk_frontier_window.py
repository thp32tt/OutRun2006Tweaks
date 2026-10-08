#!/usr/bin/env python3
"""Fail-closed validator for DXVK disassembly frontier windows.

This helper validates raw evidence continuity only. It intentionally does not
perform instruction semantic recovery or runtime claims.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FrontierWindow:
    start_rva: str
    end_rva: str
    previous_end_rva: str
    overlap_hex: str


def validate_frontier(window: FrontierWindow) -> None:
    assert window.start_rva == window.previous_end_rva
    assert int(window.end_rva, 16) > int(window.start_rva, 16)
    assert len(bytes.fromhex(window.overlap_hex)) > 0


def main() -> None:
    validate_frontier(
        FrontierWindow(
            start_rva="0x00182F7E",
            end_rva="0x00182FBE",
            previous_end_rva="0x00182F7E",
            overlap_hex="66 0f 54 1d 20 91 61",
        )
    )
    print("DXVK_FRONTIER_WINDOW_VALIDATOR=PASS")


if __name__ == "__main__":
    main()
