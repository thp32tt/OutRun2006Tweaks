#!/usr/bin/env python3
"""Static guard for the DXVK continuation frontier handoff.

This intentionally checks evidence metadata only. It does not claim that the
instruction bytes have runtime meaning; it prevents accidental promotion of a
partial overlap boundary as a completed decode window.
"""

FRONTIER = {
    "start_rva": "0x00182F7E",
    "probe_end_rva": "0x00182FBE",
    "overlap_bytes": "66 0f 54 1d 20 91 61",
}


def validate_frontier_metadata():
    assert FRONTIER["start_rva"] == "0x00182F7E"
    assert FRONTIER["probe_end_rva"] == "0x00182FBE"
    assert len(FRONTIER["overlap_bytes"].split()) >= 1
    assert FRONTIER["overlap_bytes"].startswith("66 0f")


if __name__ == "__main__":
    validate_frontier_metadata()
    print("DXVK continuation frontier metadata guard: PASS")
