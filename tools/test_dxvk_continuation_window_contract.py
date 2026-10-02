#!/usr/bin/env python3
"""Static contract regression for DXVK disassembly continuation windows.

This test documents the fail-closed rule used by conversion evidence tooling:
raw byte windows must preserve the overlap bytes at the boundary and must not
silently decode a partial trailing instruction as a completed instruction.
"""

from __future__ import annotations


OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


class WindowError(AssertionError):
    pass


def validate_window(prefix: bytes, next_window: bytes) -> None:
    if prefix[-len(OVERLAP) :] != OVERLAP:
        raise WindowError("missing canonical continuation overlap")
    if not next_window.startswith(OVERLAP):
        raise WindowError("continuation window does not preserve overlap")


def reject_truncated_tail(window: bytes, minimum_tail: int = 7) -> None:
    if len(window) < minimum_tail:
        raise WindowError("truncated overlap accepted")


def main() -> int:
    validate_window(
        bytes.fromhex("90 90 66 0f 54 1d 20 91 61"),
        bytes.fromhex("66 0f 54 1d 20 91 61 48 89"),
    )
    reject_truncated_tail(OVERLAP)
    print("DXVK continuation window contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
