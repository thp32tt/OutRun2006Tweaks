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
    r"(?: vkHandles=(?P<vkHandles>[01]) vkQueue=(?P<vkQueue>[01]) "
    r"extMemoryWin32=(?P<extMemoryWin32>[01]) "
    r"extSemaphoreWin32=(?P<extSemaphoreWin32>[01]) "
    r"nativeTransportCandidate=(?P<nativeTransportCandidate>[01]) "
    r"queueFamily=(?P<queueFamily>\d+) queueIndex=(?P<queueIndex>\d+))?"
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
                        "stock_vk_handles": (
                            bool(int(data["vkHandles"]))
                            if data.get("vkHandles") is not None
                            else None
                        ),
                        "stock_vk_submission_queue": (
                            bool(int(data["vkQueue"]))
                            if data.get("vkQueue") is not None
                            else None
                        ),
                        "external_memory_win32": (
                            bool(int(data["extMemoryWin32"]))
                            if data.get("extMemoryWin32") is not None
                            else None
                        ),
                        "external_semaphore_win32": (
                            bool(int(data["extSemaphoreWin32"]))
                            if data.get("extSemaphoreWin32") is not None
                            else None
                        ),
                        "native_transport_candidate": (
                            bool(int(data["nativeTransportCandidate"]))
                            if data.get("nativeTransportCandidate") is not None
                            else None
                        ),
                        "queue_family_index": (
                            int(data["queueFamily"])
                            if data.get("queueFamily") is not None
                            else None
                        ),
                        "queue_index": (
                            int(data["queueIndex"])
                            if data.get("queueIndex") is not None
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
    creation_attestation_ids = [
        probe.get("attestation") for probe in creation_probes
    ]
    creation_attestation_ids_valid = bool(creation_probes) and all(
        isinstance(attestation, int) and attestation > 0
        for attestation in creation_attestation_ids
    ) and len(set(creation_attestation_ids)) == len(creation_attestation_ids)
    # ProviderAttestationSequence is process-global and strictly increasing.
    # Log-file enumeration is not a trustworthy chronology, so select the
    # newest creation evidence by producer sequence instead of file order.
    latest_creation = (
        max(creation_probes, key=lambda probe: probe["attestation"])
        if creation_attestation_ids_valid
        else (creation_probes[-1] if creation_probes else None)
    )
    latest = latest_creation if latest_creation is not None else (probes[-1] if probes else None)
    creation_re_attestation_passed = creation_attestation_ids_valid and all(
        probe["provider_loaded"]
        and probe["non_system"]
        and probe["game_local"]
        and probe["stock_interop"]
        for probe in creation_probes
    )
    expected_version = None
    provider_hash = None
    expected_provider_hash = None
    if isinstance(preflight, dict) and isinstance(preflight.get("Dxvk"), dict):
        expected_version = preflight["Dxvk"].get("Version")
        provider = preflight["Dxvk"].get("Provider")
        if isinstance(provider, dict):
            provider_hash = provider.get("Sha256")
        expected_provider_hash = preflight["Dxvk"].get("ExpectedSha256")

    sha256_re = re.compile(r"^[0-9A-Fa-f]{64}$")
    provider_hash_valid = (
        isinstance(provider_hash, str) and sha256_re.fullmatch(provider_hash) is not None
    )
    expected_provider_hash_valid = (
        isinstance(expected_provider_hash, str)
        and sha256_re.fullmatch(expected_provider_hash) is not None
    )
    provider_hash_matches_expected = None
    if provider_hash_valid and expected_provider_hash_valid:
        provider_hash_matches_expected = (
            provider_hash.lower() == expected_provider_hash.lower()
        )

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
    elif not creation_attestation_ids_valid:
        status = "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID"
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
    elif provider_hash is None or expected_provider_hash is None:
        status = "DXVK_PREFLIGHT_PROVIDER_SHA256_MISSING"
    elif not provider_hash_valid or not expected_provider_hash_valid:
        status = "DXVK_PREFLIGHT_PROVIDER_SHA256_INVALID"
    elif provider_hash_matches_expected is not True:
        status = "DXVK_PREFLIGHT_PROVIDER_SHA256_MISMATCH"
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
        "DeviceCreationAttestationIds": creation_attestation_ids,
        "DeviceCreationAttestationIdsValid": creation_attestation_ids_valid,
        "PreflightDxvkVersion": expected_version,
        "PreflightProviderSha256": provider_hash,
        "PreflightExpectedProviderSha256": expected_provider_hash,
        "PreflightProviderSha256Valid": provider_hash_valid,
        "PreflightExpectedProviderSha256Valid": expected_provider_hash_valid,
        "PreflightProviderSha256MatchesExpected": provider_hash_matches_expected,
        "DetectedDxvkVersions": unique_versions,
        "RuntimeVersionMatchesPreflight": version_match,
        "NativeTransportPrerequisitesObserved": (
            latest.get("native_transport_candidate") if latest else None
        ),
        "NativeTransportPrerequisiteNote": (
            "Passive capability evidence only. A true cross-process DXVK transport "
            "still requires explicit external-memory allocation/export/import plus "
            "generation/fence/consumer-ACK synchronization before runtime use."
        ),
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
