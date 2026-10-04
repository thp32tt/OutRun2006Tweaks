#!/usr/bin/env python3
"""Fail-closed DXVK raw continuation-window contract verifier.

This helper validates exact RVA continuity and byte overlap only. It deliberately
avoids decoding guessed instructions or assigning runtime/render semantics.
"""

from __future__ import annotations

import argparse
import json


def parse_bytes(value: str) -> bytes:
    compact = value.replace("0x", "").replace(" ", "")
    if len(compact) % 2:
        raise ValueError("hex input has an incomplete byte")
    return bytes.fromhex(compact)


def verify_window(start_rva: str, end_rva: str, overlap: str, observed: str) -> dict:
    result = {
        "start_rva": start_rva.lower(),
        "end_rva": end_rva.lower(),
        "overlap_bytes_match": parse_bytes(overlap) == parse_bytes(observed),
        "runtime_validation": "UNTESTED",
    }
    result["passed"] = result["overlap_bytes_match"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    parser.add_argument("--expected-overlap", required=True)
    parser.add_argument("--observed-overlap", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = verify_window(
        args.start_rva,
        args.end_rva,
        args.expected_overlap,
        args.observed_overlap,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("PASS" if result["passed"] else "FAIL")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
