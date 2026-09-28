#!/usr/bin/env python3
"""Extract stock-DXVK provider/runtime identity from one OutRun VR session."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROBE_RE = re.compile(
    r"VR DXVK R71 census: providerLoaded=(?P<providerLoaded>[01]) "
    r"nonSystem=(?P<nonSystem>[01]) gameLocal=(?P<gameLocal>[01]) "
    r"stockInterop=(?P<stockInterop>[01]) D3D9Ex=(?P<d3d9Ex>[01]) "
    r"stockHr=0x(?P<stockHr>[0-9A-Fa-f]+) exHr=0x(?P<exHr>[0-9A-Fa-f]+)"
    r"(?: source=(?P<source>[A-Za-z0-9_.-]+) "
    r"attestation=(?P<attestation>\d+))?"
)

DXVK_VERSION_RE = re.compile(r"DXVK:\s*v?(?P<version>\d+\.\d+(?:\.\d+)?)", re.I)
DEVICE_RE = re.compile(r"(?:Device|GPU).*?:\s*(?P<value>.+)", re.I)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    session = Path(args.session_dir)
    output = Path(args.output)

    probes: list[dict] = []
    dxvk_log_files: list[str] = []
    detected_versions: list[str] = []
    device_lines: list[str] = []

    for path in sorted(session.glob("*.log")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line in text.splitlines():
            match = PROBE_RE.search(line)
            if match:
                data = match.groupdict()
                probes.append(
                    {
                        "provider_loaded": bool(int(data["providerLoaded"])),
                        "non_system": bool(int(data["nonSystem"])),
                        "game_local": bool(int(data["gameLocal"])),
                        "stock_interop": bool(int(data["stockInterop"])),
                        "d3d9_ex": bool(int(data["d3d9Ex"])),
                        "stock_interop_hr_hex": "0x" + data["stockHr"].upper(),
                        "d3d9_ex_hr_hex": "0x" + data["exHr"].upper(),
                        "source": data.get("source") or "",
                        "attestation": (
                            int(data["attestation"])
                            if data.get("attestation")
                            else None
                        ),
                    }
                )

        if path.name.lower().endswith("_d3d9.log") or "dxvk" in path.name.lower():
            dxvk_log_files.append(path.name)
            for line in text.splitlines():
                version = DXVK_VERSION_RE.search(line)
                if version:
                    detected_versions.append(version.group("version"))
                if len(device_lines) < 32 and (
                    "device" in line.lower() or "adapter" in line.lower()
                ):
                    device_lines.append(line.strip())

    preflight_path = session / "VR_ONE_CLICK_PREFLIGHT.json"
    preflight = None
    if preflight_path.exists():
        try:
            preflight = json.loads(preflight_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            preflight = None

    creation_probes = [
        probe
        for probe in probes
        if probe.get("source", "").startswith("create-device-")
    ]
    latest = creation_probes[-1] if creation_probes else (probes[-1] if probes else None)
    creation_re_attestation_passed = bool(creation_probes) and all(
        probe["provider_loaded"]
        and probe["non_system"]
        and probe["game_local"]
        and probe["stock_interop"]
        for probe in creation_probes
    )
    expected_version = None
    expected_hash = None
    if isinstance(preflight, dict) and isinstance(preflight.get("Dxvk"), dict):
        expected_version = preflight["Dxvk"].get("Version")
        provider = preflight["Dxvk"].get("Provider")
        if isinstance(provider, dict):
            expected_hash = provider.get("Sha256")

    unique_versions = sorted(set(detected_versions))
    version_match = None
    if expected_version and unique_versions:
        # Exact runtime-version proof is part of the stock-provider verdict.
        # Multiple distinct version lines are ambiguous evidence and must not
        # satisfy the stock-version attestation.
        version_match = (
            len(unique_versions) == 1 and unique_versions[0] == expected_version
        )

    if latest is None:
        status = "NO_DXVK_PROVIDER_CENSUS"
    elif not creation_probes:
        status = "DXVK_DEVICE_CREATION_REATTESTATION_MISSING"
    elif not creation_re_attestation_passed:
        status = "DXVK_DEVICE_CREATION_REATTESTATION_FAILED"
    elif not latest["provider_loaded"]:
        status = "D3D9_PROVIDER_NOT_LOADED"
    elif not latest["non_system"]:
        status = "SYSTEM_D3D9_PROVIDER_ACTIVE"
    elif not latest["game_local"]:
        status = "NONLOCAL_D3D9_PROVIDER_ACTIVE"
    elif not latest["stock_interop"]:
        status = "GAME_LOCAL_PROVIDER_WITHOUT_STOCK_DXVK_INTEROP"
    elif not expected_version:
        status = "DXVK_PREFLIGHT_VERSION_MISSING"
    elif not unique_versions:
        status = "DXVK_RUNTIME_VERSION_UNOBSERVED"
    elif version_match is not True:
        status = "DXVK_RUNTIME_VERSION_MISMATCH"
    else:
        status = "STOCK_DXVK_PROVIDER_VERIFIED"

    report = {
        "SchemaVersion": 2,
        "Status": status,
        "MultiviewPromotionAllowed": False,
        "PromotionNote": (
            "Stock provider identity is necessary but not sufficient. "
            "DXVK multiview remains disabled until SAFE/two-pass visual, Reset, "
            "menu, HUD, flare and world-marker parity gates pass."
        ),
        "ProviderProbe": latest,
        "AllProviderProbes": probes,
        "DeviceCreationReattestations": creation_probes,
        "DeviceCreationReattestationCount": len(creation_probes),
        "DeviceCreationReattestationPassed": creation_re_attestation_passed,
        "PreflightDxvkVersion": expected_version,
        "PreflightProviderSha256": expected_hash,
        "DetectedDxvkVersions": unique_versions,
        "RuntimeVersionMatchesPreflight": version_match,
        "DxvkLogFiles": sorted(set(dxvk_log_files)),
        "DeviceEvidence": device_lines,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"DXVK session extraction: status={status} "
        f"probes={len(probes)} createAttest={len(creation_probes)} "
        f"logs={len(dxvk_log_files)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
