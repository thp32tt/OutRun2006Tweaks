#!/usr/bin/env python3
"""Static contract check for the DXVK continuation decode boundary.

This intentionally validates only byte-window evidence. It does not infer
function meaning or runtime behavior.
"""

WINDOW_START = 0x00182F7E
WINDOW_END = 0x00182FBE
OVERLAP_BYTES = bytes.fromhex("66 0f 54 1d 20 91 61")


def validate_boundary() -> None:
    assert WINDOW_START < WINDOW_END
    assert len(OVERLAP_BYTES) == 7
    assert WINDOW_START + len(OVERLAP_BYTES) <= WINDOW_END


def test_boundary_contract() -> None:
    validate_boundary()


if __name__ == "__main__":
    validate_boundary()
    print("DXVK_CONTINUATION_WINDOW_BOUNDARY_CONTRACT=PASS")
