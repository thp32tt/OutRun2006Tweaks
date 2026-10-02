"""Static contract tests for DXVK disassembly frontier overlap handling.

This intentionally stays byte/provenance focused. It does not promote any runtime
semantic interpretation of the recovered instructions.
"""

from dataclasses import dataclass

from dxvk_disasm_frontier_validator import (
    DisasmWindow,
    validate_contiguous_window,
)


@dataclass(frozen=True)
class FrontierWindow:
    start_rva: int
    end_rva: int
    overlap: bytes


def validate_frontier_window(window: FrontierWindow, previous_end: int, previous_tail: bytes) -> None:
    assert window.start_rva == previous_end
    assert len(window.overlap) == len(previous_tail)
    assert window.overlap == previous_tail
    assert window.end_rva > window.start_rva


def test_continuation_window_preserves_partial_instruction_overlap() -> None:
    previous_tail = bytes.fromhex("66 0f 54 1d 20 91 61")
    window = FrontierWindow(
        start_rva=0x00182F7E,
        end_rva=0x00182FBE,
        overlap=previous_tail,
    )

    validate_frontier_window(window, 0x00182F7E, previous_tail)
    validate_contiguous_window(
        DisasmWindow(0x00182F7E, 0x00182FBE, previous_tail),
        0x00182F7E,
        previous_tail,
    )


def test_frontier_window_rejects_different_overlap() -> None:
    previous_tail = bytes.fromhex("66 0f 54 1d 20 91 61")
    window = FrontierWindow(
        start_rva=0x00182F7E,
        end_rva=0x00182FBE,
        overlap=bytes.fromhex("66 0f 54 1d 20 91 60"),
    )

    try:
        validate_frontier_window(window, 0x00182F7E, previous_tail)
    except AssertionError:
        return
    raise AssertionError("non-matching frontier overlap was accepted")
