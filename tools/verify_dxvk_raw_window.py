#!/usr/bin/env python3
"""Fail-closed verifier for DXVK raw disassembly continuation windows.

This tool intentionally does not assign runtime semantics.  It only validates
that a captured byte window contains the expected overlap bytes and that the
window boundaries are internally consistent before a later decoder step.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


class WindowVerificationError(RuntimeError):
    pass


def verify_window(data: bytes, *, start_rva: int, expected_overlap: bytes, expected_sha256: str | None = None) -> dict[str, object]:
    if start_rva < 0:
        raise WindowVerificationError("start RVA must be non-negative")
    if not expected_overlap:
        raise WindowVerificationError("overlap bytes must not be empty")
    if not data.startswith(expected_overlap):
        raise WindowVerificationError("continuation overlap bytes do not match capture edge")

    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise WindowVerificationError("capture digest mismatch")

    return {
        "start_rva": hex(start_rva),
        "length": len(data),
        "sha256": digest,
        "overlap_match": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("window", type=Path)
    parser.add_argument("--start-rva", required=True, type=lambda value: int(value, 0))
    parser.add_argument("--overlap", required=True, help="hex bytes, e.g. '66 0f 54 1d'")
    parser.add_argument("--sha256")
    args = parser.parse_args()

    result = verify_window(
        args.window.read_bytes(),
        start_rva=args.start_rva,
        expected_overlap=bytes.fromhex(args.overlap),
        expected_sha256=args.sha256,
    )
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
