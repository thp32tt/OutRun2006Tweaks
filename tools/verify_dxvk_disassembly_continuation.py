#!/usr/bin/env python3
"""Fail-closed verifier for DXVK disassembly continuation captures.

This tool intentionally validates only byte-window continuity. It does not
promote function meaning or runtime behavior from disassembly evidence.
"""

from __future__ import annotations

import argparse



def verify_overlap(capture_hex: str, overlap_hex: str, next_hex: str) -> None:
    capture = bytes.fromhex(capture_hex)
    overlap = bytes.fromhex(overlap_hex)
    following = bytes.fromhex(next_hex)

    if not overlap:
        raise ValueError("overlap window must not be empty")
    if not capture.endswith(overlap):
        raise ValueError("capture does not end with required overlap bytes")
    if not following.startswith(overlap):
        raise ValueError("continuation does not preserve overlap bytes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, help="captured hex bytes")
    parser.add_argument("--overlap", required=True, help="boundary overlap hex bytes")
    parser.add_argument("--next", dest="next_window", required=True, help="next raw window hex bytes")
    args = parser.parse_args()

    verify_overlap(args.capture, args.overlap, args.next_window)
    print("DXVK_CONTINUATION_OVERLAP=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
