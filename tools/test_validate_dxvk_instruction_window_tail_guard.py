#!/usr/bin/env python3
"""Regression guard for DXVK disassembly tail handling.

The continuation scanner must reject truncated tails before attempting to
compare overlap bytes. This keeps incomplete x86 windows explicit instead of
silently treating missing bytes as a valid decode boundary.
"""

MIN_TAIL = bytes.fromhex("66 0f 54 1d 20 91 61")


def require_complete_tail(tail: bytes) -> None:
    if len(tail) != len(MIN_TAIL):
        raise AssertionError("DXVK continuation tail must contain complete overlap bytes")
    if tail != MIN_TAIL:
        raise AssertionError("DXVK continuation tail bytes changed unexpectedly")


def test_rejects_truncated_tail():
    try:
        require_complete_tail(MIN_TAIL[:-1])
    except AssertionError:
        return
    raise AssertionError("truncated continuation tail was accepted")


def test_accepts_canonical_tail():
    require_complete_tail(MIN_TAIL)


if __name__ == "__main__":
    test_rejects_truncated_tail()
    test_accepts_canonical_tail()
    print("DXVK continuation tail guard: PASS")
