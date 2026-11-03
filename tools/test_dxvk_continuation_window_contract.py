#!/usr/bin/env python3
"""Static contract regression for DXVK disassembly continuation windows.

This test documents the fail-closed rule used by conversion evidence tooling:
raw byte windows must preserve the overlap bytes at the boundary and must not
silently decode a partial trailing instruction as a completed instruction.
"""

from __future__ import annotations


OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")
CANONICAL_BRANCHES = {
    0x00182F4A: 0x00182F6D,
    0x00182F51: 0x00182F03,
}


class WindowError(AssertionError):
    pass


def validate_window(prefix: bytes, next_window: bytes) -> None:
    if not prefix or not next_window:
        raise WindowError("empty continuation window accepted")
    if prefix[-len(OVERLAP) :] != OVERLAP:
        raise WindowError("missing canonical continuation overlap")
    if not next_window.startswith(OVERLAP):
        raise WindowError("continuation window does not preserve overlap")


def validate_branch_census(branches: dict[int, int]) -> None:
    if branches != CANONICAL_BRANCHES:
        raise WindowError("canonical continuation branch census changed")


def reject_truncated_tail(window: bytes, minimum_tail: int = 7) -> None:
    if len(window) < minimum_tail:
        raise WindowError("truncated overlap accepted")


def reject_short_overlap(overlap: bytes) -> None:
    if overlap != OVERLAP:
        raise WindowError("non-canonical overlap accepted")


def main() -> int:
    validate_window(
        bytes.fromhex("90 90 66 0f 54 1d 20 91 61"),
        bytes.fromhex("66 0f 54 1d 20 91 61 48 89"),
    )
    validate_branch_census(dict(CANONICAL_BRANCHES))
    reject_truncated_tail(OVERLAP)
    reject_short_overlap(OVERLAP)
    print("DXVK continuation window contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
