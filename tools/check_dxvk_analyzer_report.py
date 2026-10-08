#!/usr/bin/env python3
"""Validate fail-closed invariants in DXVK session analyzer reports.

This is a static CI helper. It does not claim runtime correctness; it checks
that analyzer output cannot accidentally promote ambiguous provider evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FAIL_CLOSED = {
    "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID",
    "DXVK_DEVICE_CREATION_REATTESTATION_MISSING",
    "DXVK_DEVICE_CREATION_REATTESTATION_FAILED",
    "DXVK_PREFLIGHT_PROVIDER_SHA256_MISSING",
    "DXVK_PREFLIGHT_PROVIDER_SHA256_INVALID",
    "DXVK_PREFLIGHT_PROVIDER_SHA256_MISMATCH",
}


def validate(report: dict) -> list[str]:
    errors: list[str] = []
    status = report.get("Status")
    verified = status == "STOCK_DXVK_PROVIDER_VERIFIED"

    if verified:
        if report.get("DeviceCreationAttestationIdsValid") is not True:
            errors.append("verified report has invalid creation attestation IDs")
        if report.get("DeviceCreationReattestationPassed") is not True:
            errors.append("verified report lacks successful creation reattestation")
        if report.get("PreflightProviderSha256MatchesExpected") is not True:
            errors.append("verified report lacks provider hash match")
        if report.get("RuntimeVersionMatchesPreflight") is not True:
            errors.append("verified report lacks exact runtime version match")

    if status in FAIL_CLOSED and verified:
        errors.append("fail-closed status was promoted to verified")

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

    print("DXVK_ANALYZER_REPORT_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
