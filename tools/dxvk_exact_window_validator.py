#!/usr/bin/env python3
"""Validate bounded DXVK disassembly raw windows without promoting semantics.

This tool intentionally checks provenance continuity only: the bytes at the
start of a continuation window must preserve the overlap captured from the
previous evidence window. It does not decode or infer runtime behavior.
"""

import argparse
import hashlib
import json
from pathlib import Path


def validate_window(data: bytes, expected_overlap: bytes, start_rva: str, end_rva: str):
    if not expected_overlap:
        raise ValueError("empty overlap is not a valid continuation proof")
    if data[: len(expected_overlap)] != expected_overlap:
        raise ValueError("continuation overlap mismatch")
    return {
        "start_rva": start_rva,
        "end_rva": end_rva,
        "overlap_bytes": expected_overlap.hex(" "),
        "window_sha256": hashlib.sha256(data).hexdigest(),
        "semantic_promotion": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("window")
    parser.add_argument("--overlap", required=True)
    parser.add_argument("--start-rva", required=True)
    parser.add_argument("--end-rva", required=True)
    args = parser.parse_args()

    result = validate_window(
        Path(args.window).read_bytes(),
        bytes.fromhex(args.overlap),
        args.start_rva,
        args.end_rva,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
