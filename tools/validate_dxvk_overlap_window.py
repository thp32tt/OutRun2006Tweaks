#!/usr/bin/env python3
"""Validate a DXVK disassembly continuation overlap window.

This is intentionally static-only. It prevents accidental analysis of a window
that does not include the required predecessor overlap bytes.
"""

import argparse
import sys


def normalize_hex(value: str) -> str:
    return "".join(value.lower().split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlap", required=True, help="validated overlap bytes")
    parser.add_argument("--expected", required=True, help="expected overlap bytes")
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    args = parser.parse_args()

    overlap = normalize_hex(args.overlap)
    expected = normalize_hex(args.expected)
    if overlap != expected:
        print("DXVK_OVERLAP_WINDOW_INVALID", file=sys.stderr)
        return 1
    if args.start_rva == args.end_rva:
        print("DXVK_OVERLAP_WINDOW_EMPTY", file=sys.stderr)
        return 1

    print("DXVK_OVERLAP_WINDOW_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
