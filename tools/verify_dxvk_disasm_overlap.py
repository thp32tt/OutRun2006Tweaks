#!/usr/bin/env python3
"""Validate a DXVK disassembly continuation overlap before semantic promotion.

This checker intentionally performs byte/provenance validation only. It does not
claim function identity or runtime behavior from a partial instruction window.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hex-file", required=True)
    parser.add_argument("--expected-overlap", required=True)
    args = parser.parse_args()

    raw = Path(args.hex_file).read_text(encoding="utf-8").split()
    actual = " ".join(byte.lower() for byte in raw)
    expected = " ".join(args.expected_overlap.lower().split())

    if not actual.startswith(expected):
        print("DXVK disassembly overlap: FAIL")
        print(f"expected prefix: {expected}")
        print(f"actual bytes:    {actual}")
        return 1

    print("DXVK disassembly overlap: PASS")
    print(f"validated prefix bytes: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
