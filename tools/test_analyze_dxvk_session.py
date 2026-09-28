#!/usr/bin/env python3
"""Regression tests for stock-DXVK runtime/device re-attestation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze_dxvk_session.py"

PROBE_BASE = (
    "VR DXVK R71 census: providerLoaded=1 nonSystem=1 gameLocal=1 "
    "stockInterop=1 D3D9Ex=1 stockHr=0x00000000 exHr=0x00000000"
)
PROBE_CREATE_EX = PROBE_BASE + " source=create-device-ex attestation=1"
PROBE_STARTUP = PROBE_BASE + " source=startup-observer attestation=2"


def run_case(
    name: str,
    *,
    expected_version: str | None,
    runtime_versions: list[str],
    expected_status: str,
    expected_match: bool | None,
    probe_lines: list[str] | None = None,
    expected_create_count: int = 1,
    expected_reattest_passed: bool = True,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"dxvk-analyzer-{name}-") as temp:
        session = Path(temp)
        preflight = {"Dxvk": {"Provider": {"Sha256": "fixture-sha256"}}}
        if expected_version is not None:
            preflight["Dxvk"]["Version"] = expected_version
        (session / "VR_ONE_CLICK_PREFLIGHT.json").write_text(
            json.dumps(preflight), encoding="utf-8"
        )

        if probe_lines is None:
            probe_lines = [PROBE_CREATE_EX, PROBE_STARTUP]
        log_lines = list(probe_lines)
        log_lines.extend(f"DXVK: v{version}" for version in runtime_versions)
        (session / "OutRun_d3d9.log").write_text(
            "\n".join(log_lines) + "\n", encoding="utf-8"
        )

        output = session / "DXVK_SESSION_SUMMARY.json"
        subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--session-dir",
                str(session),
                "--output",
                str(output),
            ],
            check=True,
        )
        report = json.loads(output.read_text(encoding="utf-8"))
        actual_status = report.get("Status")
        actual_match = report.get("RuntimeVersionMatchesPreflight")
        actual_count = report.get("DeviceCreationReattestationCount")
        actual_passed = report.get("DeviceCreationReattestationPassed")
        if (
            actual_status != expected_status
            or actual_match is not expected_match
            or actual_count != expected_create_count
            or actual_passed is not expected_reattest_passed
        ):
            raise AssertionError(
                f"{name}: status={actual_status!r} match={actual_match!r} "
                f"create_count={actual_count!r} reattest={actual_passed!r}; "
                f"expected status={expected_status!r} match={expected_match!r} "
                f"create_count={expected_create_count!r} "
                f"reattest={expected_reattest_passed!r}"
            )


def main() -> int:
    run_case(
        "verified",
        expected_version="3.1.1",
        runtime_versions=["3.1.1"],
        expected_status="STOCK_DXVK_PROVIDER_VERIFIED",
        expected_match=True,
    )
    run_case(
        "version-unobserved",
        expected_version="3.1.1",
        runtime_versions=[],
        expected_status="DXVK_RUNTIME_VERSION_UNOBSERVED",
        expected_match=None,
    )
    run_case(
        "version-mismatch",
        expected_version="3.1.1",
        runtime_versions=["3.1.0"],
        expected_status="DXVK_RUNTIME_VERSION_MISMATCH",
        expected_match=False,
    )
    run_case(
        "ambiguous-version-lines",
        expected_version="3.1.1",
        runtime_versions=["3.1.1", "3.1.0"],
        expected_status="DXVK_RUNTIME_VERSION_MISMATCH",
        expected_match=False,
    )
    run_case(
        "preflight-version-missing",
        expected_version=None,
        runtime_versions=["3.1.1"],
        expected_status="DXVK_PREFLIGHT_VERSION_MISSING",
        expected_match=None,
    )
    run_case(
        "creation-reattestation-missing",
        expected_version="3.1.1",
        runtime_versions=["3.1.1"],
        expected_status="DXVK_DEVICE_CREATION_REATTESTATION_MISSING",
        expected_match=True,
        probe_lines=[PROBE_STARTUP],
        expected_create_count=0,
        expected_reattest_passed=False,
    )
    failed_recreation = (
        "VR DXVK R71 census: providerLoaded=1 nonSystem=1 gameLocal=1 "
        "stockInterop=0 D3D9Ex=1 stockHr=0x80004002 exHr=0x00000000 "
        "source=create-device-ex attestation=3"
    )
    run_case(
        "recreation-reattestation-failed",
        expected_version="3.1.1",
        runtime_versions=["3.1.1"],
        expected_status="DXVK_DEVICE_CREATION_REATTESTATION_FAILED",
        expected_match=True,
        probe_lines=[PROBE_CREATE_EX, PROBE_STARTUP, failed_recreation],
        expected_create_count=2,
        expected_reattest_passed=False,
    )
    print("DXVK session analyzer regression tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
