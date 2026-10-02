"""Static DXVK continuation branch-target contract checks.

This keeps recovered disassembly evidence conservative: branch targets are only
accepted when they stay inside the captured canonical window or point to an
explicitly recorded predecessor target. It does not infer runtime behavior.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BranchEdge:
    source_rva: int
    target_rva: int


@dataclass(frozen=True)
class CapturedWindow:
    start_rva: int
    end_rva: int
    predecessor_targets: tuple[int, ...]


def validate_branch_edge(window: CapturedWindow, edge: BranchEdge) -> bool:
    if edge.source_rva < window.start_rva or edge.source_rva >= window.end_rva:
        return False
    return window.start_rva <= edge.target_rva < window.end_rva or edge.target_rva in window.predecessor_targets


def test_accepts_canonical_182f45_frontier_targets():
    window = CapturedWindow(
        start_rva=0x00182F45,
        end_rva=0x00182FBE,
        predecessor_targets=(0x00182F6A,),
    )
    assert validate_branch_edge(window, BranchEdge(0x00182F4A, 0x00182F6D))
    assert validate_branch_edge(window, BranchEdge(0x00182F51, 0x00182F03)) is False


def test_rejects_target_outside_without_provenance():
    window = CapturedWindow(
        start_rva=0x00182F7E,
        end_rva=0x00182FBE,
        predecessor_targets=(),
    )
    assert not validate_branch_edge(window, BranchEdge(0x00182F80, 0x00190000))
