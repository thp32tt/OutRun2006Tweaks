#!/usr/bin/env python3
"""Fail-closed static checker for DXVK session attestation reports.

This verifier intentionally checks only evidence contracts. It does not promote
runtime readiness or make any Quest/VDXR validation claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_KEYS = {
    "SchemaVersion",
    "Status",
    "DeviceCreationAttestationIdsValid",
    "DeviceCreationReattestationPassed",
    "RuntimeVersionMatchesPreflight",
}


BAD_STATUSES = {
    "NO_DXVK_PROVIDER_CENSUS",
    "DXVK_DEVICE_CREATION_REATTESTATION_MISSING",
    "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID",
    "DXVK_DEVICE_CREATION_REATTESTATION_FAILED",
}


def verify(report: dict) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - report.keys())
    if missing:
        errors.append("missing_keys=" + ",".join(missing))

    status = report.get("Status")
    if status in BAD_STATUSES:
        errors.append("invalid_status=" + str(status))

    if report.get("DeviceCreationAttestationIdsValid") is not True:
        errors.append("creation_attestation_ids_not_valid")

    if report.get("DeviceCreationReattestationPassed") is not True:
        errors.append("creation_reattestation_not_passed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    errors = verify(report)
    if errors:
        print("DXVK attestation contract: FAIL")
        for error in errors:
            print(error)
        return 1

    print("DXVK attestation contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
