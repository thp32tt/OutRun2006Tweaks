#!/usr/bin/env python3
"""Regression checks for DXVK canonical disassembly overlap boundaries.

This intentionally validates evidence metadata only. It does not promote runtime
semantics from disassembly bytes.
"""

EXPECTED = {
    "frontier_start": "0x00182F7E",
    "probe_end": "0x00182FBE",
    "overlap": "66 0f 54 1d 20 91 61",
}


def validate_frontier(record):
    for key, value in EXPECTED.items():
        if record.get(key) != value:
            raise AssertionError(f"DXVK frontier mismatch: {key}")
    return True


def test_known_frontier():
    assert validate_frontier(
        {
            "frontier_start": "0x00182F7E",
            "probe_end": "0x00182FBE",
            "overlap": "66 0f 54 1d 20 91 61",
        }
    )


if __name__ == "__main__":
    test_known_frontier()
    print("DXVK overlap frontier guard: PASS")
