#!/usr/bin/env python3
"""Validate DXVK creation attestation ordering from analyzer JSON output.

This is a static evidence helper. It does not promote runtime identity; it only
checks that producer attestation IDs used for creation evidence are strictly
increasing when a sequence is supplied.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    ids = report.get("DeviceCreationAttestationIds", [])
    if not isinstance(ids, list):
        raise SystemExit("DeviceCreationAttestationIds must be a list")

    if any(not isinstance(value, int) or value <= 0 for value in ids):
        raise SystemExit("invalid DXVK creation attestation id")

    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise SystemExit("DXVK creation attestation sequence is not strictly ordered")

    print(f"DXVK attestation sequence: OK count={len(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
