#!/usr/bin/env python3
"""Deterministic source-policy checks for the 2026-09-21 OutRun VR finding bundle."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(path: str, markers: list[str]) -> None:
    text = read(path)
    missing = [m for m in markers if m not in text]
    if missing:
        raise AssertionError(f"{path}: missing expected markers: {missing}")

def forbid(path: str, markers: list[str]) -> None:
    text = read(path)
    present = [m for m in markers if m in text]
    if present:
        raise AssertionError(f"{path}: forbidden regression markers present: {present}")

def main() -> int:
    require("src/vr/d3d9/stereo_renderer_r30.cpp", [
        "clipCorrection._11 = hudScaleX * eyeScale[eye];",
        "R30TransformHudScissor(",
        "device->SetScissorRect(&eyeScissor[0])",
        "device->SetScissorRect(&eyeScissor[1])",
        "IDirect3DTexture9* compositeSource =",
        "compositeSource = R30SkyGlow.temp[eye];",
    ])
    require("src/vr/d3d9/stereo_renderer_r34.cpp", [
        "device->TestCooperativeLevel()",
        "D3DERR_DEVICELOST",
        "D3DERR_DEVICENOTRESET",
        "R34LostDeviceBypasses",
    ])
    require("src/vr/d3d9/ex_device_upgrade_r15.cpp", [
        "R15CaptureClassicExtraBaseline",
        "R15RestoreClassicExtraBaseline",
        "no pre-Reset state-block replay",
        "RestoreClassicResetState(device)",
    ])
    forbid("src/vr/d3d9/ex_device_upgrade_r15.cpp", [
        "R15ClassicStateBlock",
        "R15ResetStateBlock",
    ])
    require("src/vr/debug/hud_inspector.cpp", [
        "InspectorActive",
        "SemanticIdentityVerified",
        "OUTRUN_VR_EXE_SEMANTICS_VERIFIED",
        "MakeKey(kind, callRva, arg0, arg1, mode, stage)",
        "TraceFile.flush();",
        "ResetTraceState()",
    ])
    require("src/hooks_textures.cpp", [
        "ApplyHudInspectorFeeds",
        "Settings::VREnabled && Settings::VRHudInspector",
        "Settings::UITextureReplacement || ApplyHudInspectorFeeds",
    ])
    require("tools/analyze_outrun_exe.py", [
        '0x02D0C0: "put_sprite_ex2"',
    ])
    require("tools/Run-OutRunVRTest.ps1", [
        "LaunchConfigSha256",
        "OUTRUN_VR_EXE_SEMANTICS_VERIFIED",
        "Configuration identity is still inconsistent after session rotation.",
    ])
    require("tools/Collect-OutRunVRLogs.ps1", [
        "CONFIG_DRIFT_STATUS",
        "CollectionConfigSha256",
        "ConfigDriftStatus",
    ])
    require("src/vr/d3d9/stereo_renderer_r7.inc", [
        "RuntimeStereoEligible()",
        "IsRuntimeStereoActive() noexcept",
        "Settings::VRDirectGpuOnly && Settings::VRPreferD3D9Ex",
    ])
    require("src/hooks_graphics.cpp", [
        "!OutRunVRStereo::IsRuntimeStereoActive()",
    ])
    require("src/vr/settings.cpp", [
        "DirectGpuOnly requires PreferD3D9Ex",
        "const bool effectiveDirectOnly",
        "OUTRUN_VR_DIRECT_TRANSPORT",
    ])
    print("2026-09-21 VR finding bundle deterministic verification passed.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise
