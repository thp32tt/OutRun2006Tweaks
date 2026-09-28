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

    latest = probes[-1] if probes else None
    expected_version = None
    expected_hash = None
    if isinstance(preflight, dict) and isinstance(preflight.get("Dxvk"), dict):
        expected_version = preflight["Dxvk"].get("Version")
        provider = preflight["Dxvk"].get("Provider")
        if isinstance(provider, dict):
            expected_hash = provider.get("Sha256")

    version_match = None
    if expected_version and detected_versions:
        version_match = expected_version in detected_versions

    if latest is None:
        status = "NO_DXVK_PROVIDER_CENSUS"
    elif not latest["provider_loaded"]:
        status = "D3D9_PROVIDER_NOT_LOADED"
    elif not latest["non_system"]:
        status = "SYSTEM_D3D9_PROVIDER_ACTIVE"
    elif not latest["game_local"]:
        status = "NONLOCAL_D3D9_PROVIDER_ACTIVE"
    elif not latest["stock_interop"]:
        status = "GAME_LOCAL_PROVIDER_WITHOUT_STOCK_DXVK_INTEROP"
    elif version_match is False:
        status = "DXVK_RUNTIME_VERSION_MISMATCH"
    else:
        status = "STOCK_DXVK_PROVIDER_VERIFIED"

    report = {
        "SchemaVersion": 1,
        "Status": status,
        "MultiviewPromotionAllowed": False,
        "PromotionNote": (
            "Stock provider identity is necessary but not sufficient. "
            "DXVK multiview remains disabled until SAFE/two-pass visual, Reset, "
            "menu, HUD, flare and world-marker parity gates pass."
        ),
        "ProviderProbe": latest,
        "AllProviderProbes": probes,
        "PreflightDxvkVersion": expected_version,
        "PreflightProviderSha256": expected_hash,
        "DetectedDxvkVersions": sorted(set(detected_versions)),
        "RuntimeVersionMatchesPreflight": version_match,
        "DxvkLogFiles": sorted(set(dxvk_log_files)),
        "DeviceEvidence": device_lines,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"DXVK session extraction: status={status} "
        f"probes={len(probes)} logs={len(dxvk_log_files)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
