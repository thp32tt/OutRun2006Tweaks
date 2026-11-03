#!/usr/bin/env python3
"""Fail-closed validator for DXVK disassembly frontier manifests.

This validator intentionally checks only static evidence integrity. It does not
promote disassembly into runtime/render semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REQUIRED_KEYS = (
    "canonical_exe_sha256",
    "proof_start_rva",
    "proof_end_rva",
    "instruction_count",
    "artifact_digest",
)


def fail(message: str) -> int:
    print(f"INVALID_DXVK_FRONTIER_MANIFEST: {message}", file=sys.stderr)
    return 1


def validate(data: dict) -> int:
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        return fail("missing keys: " + ", ".join(missing))

    if not isinstance(data["instruction_count"], int) or data["instruction_count"] <= 0:
        return fail("instruction_count must be a positive integer")

    start = int(str(data["proof_start_rva"]), 16)
    end = int(str(data["proof_end_rva"]), 16)
    if end <= start:
        return fail("proof range is not forward")

    sha = str(data["canonical_exe_sha256"])
    if len(sha) != 64:
        return fail("canonical_exe_sha256 must be SHA256 length")
    try:
        int(sha, 16)
    except ValueError:
        return fail("canonical_exe_sha256 is not hexadecimal")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"cannot read manifest: {exc}")
    if not isinstance(data, dict):
        return fail("root must be an object")
    return validate(data)


if __name__ == "__main__":
    sys.exit(main())
