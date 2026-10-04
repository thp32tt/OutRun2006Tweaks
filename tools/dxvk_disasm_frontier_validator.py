"""Static helpers for DXVK disassembly frontier continuity checks.

The validator is intentionally byte-window based. It verifies recovered static
artifacts keep contiguous analysis windows without making runtime claims.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DisasmWindow:
    start_rva: int
    end_rva: int
    bytes_prefix: bytes


def validate_contiguous_window(
    window: DisasmWindow,
    expected_start: int,
    previous_window_tail: bytes,
) -> None:
    """Validate that a recovered window begins at the prior decode frontier."""

    if window.start_rva != expected_start:
        raise ValueError("DXVK disassembly window has a discontinuous start")

    if window.bytes_prefix != previous_window_tail:
        raise ValueError("DXVK disassembly window overlap does not match")

    if window.end_rva <= window.start_rva:
        raise ValueError("DXVK disassembly window has no forward progress")
