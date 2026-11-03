#!/usr/bin/env python3
"""Fail-closed verifier for DXVK disassembly continuation overlap windows.

This tool validates byte-window/provenance contracts only. It does not infer
functions, render ownership, or runtime behavior from disassembly bytes.
"""

import argparse
import json


def parse_hex(value: str) -> bytes:
    compact = value.replace("0x", "").replace(" ", "")
    if len(compact) % 2:
        raise ValueError("hex byte input must contain complete bytes")
    return bytes.fromhex(compact)


def verify(expected_rva: str, actual_rva: str, expected_bytes: str, actual_bytes: str) -> dict:
    result = {
        "expected_rva": expected_rva.lower(),
        "actual_rva": actual_rva.lower(),
        "bytes_match": parse_hex(expected_bytes) == parse_hex(actual_bytes),
        "provenance_match": expected_rva.lower() == actual_rva.lower(),
        "runtime_validation": "UNTESTED",
    }
    result["passed"] = result["bytes_match"] and result["provenance_match"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-rva", required=True)
    parser.add_argument("--actual-rva", required=True)
    parser.add_argument("--expected-bytes", required=True)
    parser.add_argument("--actual-bytes", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = verify(
        args.expected_rva,
        args.actual_rva,
        args.expected_bytes,
        args.actual_bytes,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("PASS" if result["passed"] else "FAIL")
        print(result)

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
