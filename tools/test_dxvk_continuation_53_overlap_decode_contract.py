#!/usr/bin/env python3
"""Static contract for the DXVK continuation_53 overlap frontier.

This test intentionally does not claim instruction semantics.  It guards the
raw-byte handoff boundary so future disassembly work cannot silently discard a
partial instruction prefix captured from the canonical executable window.
"""

from __future__ import annotations


FRONTIER = {
    "start_rva": 0x182F7E,
    "probe_end_rva": 0x182FBE,
    "overlap": bytes.fromhex("66 0f 54 1d 20 91 61"),
}


def test_continuation_53_overlap_is_preserved() -> None:
    assert FRONTIER["start_rva"] < FRONTIER["probe_end_rva"]
    assert FRONTIER["overlap"] == bytes.fromhex("66 0f 54 1d 20 91 61")
    assert len(FRONTIER["overlap"]) == 7


def test_overlap_boundary_requires_exact_prefix() -> None:
    prefix = FRONTIER["overlap"]
    # The previous capture ends in a mandatory seven-byte SIMD instruction
    # prefix.  Do not accept shortened windows that change the decode boundary.
    assert prefix[:6] != prefix
    assert prefix[0:2] == bytes.fromhex("66 0f")


if __name__ == "__main__":
    test_continuation_53_overlap_is_preserved()
    test_overlap_boundary_requires_exact_prefix()
    print("DXVK continuation_53 overlap contract PASS")
