#!/usr/bin/env python3
"""Static guard for DXVK disassembly continuation frontier evidence.

This intentionally validates byte-window continuity only. It does not infer
runtime/render semantics from disassembly evidence.
"""

from __future__ import annotations

import argparse
import sys


EXPECTED_OVERLAP = bytes.fromhex("66 0f 54 1d 20 91 61")


def verify_window(data: bytes, start_offset: int = 0) -> None:
    observed = data[start_offset : start_offset + len(EXPECTED_OVERLAP)]
    if observed != EXPECTED_OVERLAP:
        raise ValueError(
            "DXVK continuation overlap mismatch: "
            f"expected={EXPECTED_OVERLAP.hex(' ')} observed={observed.hex(' ')}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DXVK continuation overlap bytes")
    parser.add_argument("blob", help="binary evidence window")
    parser.add_argument("--offset", type=lambda value: int(value, 0), default=0)
    args = parser.parse_args()

    with open(args.blob, "rb") as handle:
        verify_window(handle.read(), args.offset)

    print("DXVK_CONTINUATION_FRONTIER=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
