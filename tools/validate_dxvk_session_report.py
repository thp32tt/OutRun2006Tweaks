#!/usr/bin/env python3
"""Fail-closed static validation for DXVK session analyzer reports.

This validator intentionally checks evidence shape only. It does not promote
runtime readiness or Quest/VDXR validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_KEYS = {
    "SchemaVersion",
    "Status",
    "DeviceCreationAttestationIds",
    "DeviceCreationAttestationIdsValid",
    "RuntimeVersionMatchesPreflight",
}


FAIL_CLOSED_STATUSES = {
    "NO_DXVK_PROVIDER_CENSUS",
    "DXVK_DEVICE_CREATION_REATTESTATION_MISSING",
    "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID",
    "DXVK_DEVICE_CREATION_REATTESTATION_FAILED",
}


def validate(report: dict) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_KEYS - report.keys()
    if missing:
        errors.append("missing keys: " + ",".join(sorted(missing)))

    ids = report.get("DeviceCreationAttestationIds")
    if isinstance(ids, list):
        if any(not isinstance(value, int) or value <= 0 for value in ids):
            errors.append("invalid device creation attestation id")
        if len(ids) != len(set(ids)):
            errors.append("duplicate device creation attestation id")

    status = report.get("Status")
    if status in FAIL_CLOSED_STATUSES and report.get("DeviceCreationAttestationIdsValid"):
        errors.append("fail-closed status contradicts valid attestation ids")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = validate(report)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("DXVK session report static validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
