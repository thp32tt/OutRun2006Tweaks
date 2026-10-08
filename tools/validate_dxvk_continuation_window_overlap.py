#!/usr/bin/env python3
"""Validate DXVK disassembly continuation-window overlap contracts.

This tool intentionally validates byte-boundary evidence only. It does not
assign function, render, HUD, or runtime semantics to the decoded bytes.
"""

from __future__ import annotations

import argparse


DEFAULT_OVERLAP = "66 0f 54 1d 20 91 61"


def normalize_hex(value: str) -> bytes:
    return bytes.fromhex(value.replace(",", " "))


def validate_overlap(prefix: str, continuation: str, overlap: str) -> bool:
    left = normalize_hex(prefix)
    right = normalize_hex(continuation)
    expected = normalize_hex(overlap)
    return left[-len(expected) :] == expected and right[: len(expected)] == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--continuation", required=True)
    parser.add_argument("--overlap", default=DEFAULT_OVERLAP)
    args = parser.parse_args()

    if not validate_overlap(args.prefix, args.continuation, args.overlap):
        print("DXVK_CONTINUATION_OVERLAP=FAIL")
        return 1

    print("DXVK_CONTINUATION_OVERLAP=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
