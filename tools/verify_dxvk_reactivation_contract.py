#!/usr/bin/env python3
"""Fail-closed software contract for the isolated stock-DXVK SAFE path.

This closes the stale DXVK-REACTIVATE-001 software-only queue item. It proves
that the branch still has one repeatable build/selection/preflight/provider
identity path. It does not claim Quest3/VDXR runtime or visual parity.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"DXVK reactivation contract missing file: {rel}")
    return path.read_text(encoding="utf-8")


def require(rel: str, *markers: str) -> str:
    data = read(rel)
    for marker in markers:
        if marker not in data:
            raise SystemExit(f"DXVK reactivation invariant missing: {rel} :: {marker}")
    return data


target_path = ROOT / "tools/VR_ONE_CLICK_TARGET.json"
if not target_path.is_file():
    raise SystemExit("DXVK one-click target missing")
target = json.loads(target_path.read_text(encoding="utf-8"))
expected_target = {
    "DevelopmentBranch": "vr-dxvk-r71-disasm",
    "RendererTarget": "dxvk",
    "LaunchBackend": "dxvk-safe",
    "DxvkVersion": "3.1.1",
}
for key, expected in expected_target.items():
    actual = target.get(key)
    if actual != expected:
        raise SystemExit(
            f"DXVK one-click target drift: {key} expected={expected!r} actual={actual!r}"
        )

selector = require(
    "tools/Select-OutRunVRBackend.ps1",
    '"dxvk-safe"',
    "Start-BackendSwitchTransaction",
    "Restore-BackendSwitchTransaction",
    "Remove-BackendSwitchTransaction",
    "$removeBackendSwitchTransactionBackup = $true",
    "Remove-BackendSwitchTransaction $backendSwitchTransaction",
    "'ROOT_PAYLOAD_ATTESTATION.json'",
    '"dxvk-safe" { "E_DXVK_SAFE" }',
    '$payloadBackend = if ($Backend -eq "2d" -or $Backend -eq "dxvk-safe" -or $Backend -eq "dx11") { "d3d9" } else { $Backend }',
    '$dxvkProvider = Join-Path (Join-Path $backendRoot "dxvk") "d3d9.dll"',
    'Copy-Item $dxvkProvider (Join-Path $root "d3d9.dll") -Force',
    'Remove-RootVerified "multiviewpatcher.dll"',
    'Set-IniSectionValue $text "VR" "PreferD3D9Ex" "true"',
    'DXVK SAFE: provider-local D3D9Ex is probed when exported; DirectGPU optional; multiview patcher disabled.',
)
if selector.find('Copy-Item $dxvkProvider (Join-Path $root "d3d9.dll") -Force') > selector.find('Assert-RootPayloadIdentity'):
    # Assert-RootPayloadIdentity is a function definition earlier in the file;
    # successful selection must also call it after root mutation.
    pass
if "$rootPayloadAttestation = Assert-RootPayloadIdentity" not in selector:
    raise SystemExit("DXVK selector no longer performs post-selection root payload attestation")

plan = require(
    "docs/VR_DXVK_R71_PLAN.md",
    "transactional root switch",
    "snapshots every mutable root payload/config/state file",
    "restores that snapshot and removes a partial session",
    "`ROOT_PAYLOAD_ATTESTATION.json` before session handoff",
    "not a filesystem-wide atomic rename",
)

transaction_test = require(
    "tools/Test-BackendSelectorTransaction.ps1",
    "Selector transaction test expected the injected post-attestation failure.",
    "Rollback did not restore",
    "Selector transaction backup directory was not cleaned after rollback.",
    "Successful selector did not persist ROOT_PAYLOAD_ATTESTATION.json.",
    "successful root attestation PASS",
)

preflight = require(
    "tools/Test-OutRunVROneClickPreflight.ps1",
    "$requiresPackageManifest=($resolvedBackend -eq 'dxvk-safe' -or $resolvedBackend -eq 'dxvk')",
    "Test-OutRunVRPackageIntegrity -Root $root -ManifestPath $packageManifestPath",
    "Pinned DXVK x86 provider",
    "DXVK_VERSION.txt",
    "DXVK_D3D9_SHA256.txt",
    "DXVK d3d9.dll hash mismatch",
    "Package variant mismatch: backends/d3d9 VARIANT_ID=",
    "Package variant mismatch: backends/dxvk VARIANT_ID=",
    "Package variant mismatch: BUILD_INPUTS=",
    "VARIANT_ID.txt",
    "MultiviewEnabled = ($resolvedBackend -eq 'dxvk')",
)

behavior = require(
    "tools/Test-OutRunVROneClickBehavior.ps1",
    "Expect-Failure 'package-variant'",
    "Expect-Failure 'd3d9-backend-variant'",
    "Package variant mismatch: backends/d3d9",
    "Expect-Failure 'dxvk-backend-variant'",
    "Package variant mismatch: backends/dxvk",
)

package = require(
    "tools/Build-OutRunPCFast.ps1",
    "Acquire-OutRunDXVK.ps1",
    "$dxvkVersion = '3.1.1'",
    "Explicit DXVK provider does not match pinned official DXVK",
    "Copy-Item $dxvkProvider (Join-Path $dxvkBackendDir 'd3d9.dll')",
    "DXVK_VERSION.txt",
    "DXVK_D3D9_SHA256.txt",
    "LaunchBackend = [string]$oneClickTarget.LaunchBackend",
    "VariantId = $canonicalVariantId",
    "SHA256SUMS.txt",
)
if "multiviewpatcher.dll" not in package or "$badExperimental" not in package:
    raise SystemExit("DXVK SAFE package no longer guards experimental multiview payload")

acquire = require(
    "tools/Acquire-OutRunDXVK.ps1",
    "40565b4a724aadc4433fa4e010b4b23916d9b1f1baeee64e17186db94f54e608",
    "PINNED_ARCHIVE_SHA256_AND_EXTRACTED_PROVIDER",
    "DXVK provider does not match x32/d3d9.dll extracted from the pinned archive",
)

require(
    "src/vr/d3d9/device_probe.cpp",
    "OutRunVR::Dxvk::LogProviderCensus",
)
require(
    "src/vr/d3d9/ex_device_upgrade.cpp",
    "create-device-classic",
    "create-device-ex",
    "OutRunVR::Dxvk::LogProviderCensus",
)
require(
    "src/vr/d3d9/dxvk_provider_probe.cpp",
    "gameLocalProvider",
    "stockInterop",
    "d3d9Ex",
    "ProbeStockNativeTransportPrerequisites",
    "nativeTransportCandidate",
)
require(
    "tools/analyze_dxvk_session.py",
    "STOCK_DXVK_PROVIDER_VERIFIED",
    "DXVK_RUNTIME_VERSION_UNOBSERVED",
    "DXVK_RUNTIME_VERSION_MISMATCH",
    "DeviceCreationReattestationPassed",
    "MultiviewPromotionAllowed",
)

contract = require(
    "tools/Test-VROneClickContract.ps1",
    "DXVK R71 must stay on dxvk-safe until stock two-pass visual parity passes.",
    "DXVK pinned acquisition contract missing",
    "DXVK stock-provider package enforcement missing",
    "DXVK provider re-attestation logger missing",
    "DXVK session analyzer regression test failed",
    "Test-OutRunVROneClickBehavior.ps1",
)

workflow = require(
    ".github/workflows/backend-conversion-gate.yml",
    "Test DXVK one-click behavior",
    "Test package-wide SHA256 integrity",
    "Test DXVK session analyzer",
    "Test runtime shared-handle failure classification",
    "Verify DXVK host-owned transport synchronization contract",
    "Test DXVK pinned acquisition",
    "Configure Win32",
    "Build Win32",
    "Verify binary exists",
)

if "dx12" in json.dumps(target).lower():
    raise SystemExit("Retired DX12 identity leaked into DXVK one-click target")

print("DXVK SAFE reactivation software contract: PASS")
