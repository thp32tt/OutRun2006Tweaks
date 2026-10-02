#!/usr/bin/env python3
"""Fail-closed verifier for DXVK disassembly continuation overlap windows.

This tool intentionally validates only byte-window/provenance contracts. It does
not infer functions, render ownership, or runtime behavior.
"""

import argparse
import json
from pathlib import Path


def parse_hex(value: str) -> bytes:
    return bytes.fromhex(value.replace("0x", "").replace(" ", ""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-rva", required=True)
    parser.add_argument("--actual-rva", required=True)
    parser.add_argument("--expected-bytes", required=True)
    parser.add_argument("--actual-bytes", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = {
        "expected_rva": args.expected_rva.lower(),
        "actual_rva": args.actual_rva.lower(),
        "bytes_match": parse_hex(args.expected_bytes) == parse_hex(args.actual_bytes),
        "provenance_match": args.expected_rva.lower() == args.actual_rva.lower(),
        "runtime_validation": "UNTESTED",
    }
    result["passed"] = result["bytes_match"] and result["provenance_match"]

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("PASS" if result["passed"] else "FAIL")
        print(result)

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
