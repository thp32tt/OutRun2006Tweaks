#!/usr/bin/env python3
"""Deterministic source-policy checks for the 2026-09-21 OutRun VR finding bundle."""

from pathlib import Path
import json
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
    contract = json.loads(read("docs/VR_RUNTIME_VISUAL_CONTRACT.json"))
    baseline = contract["behavioralBaseline"]
    if baseline["commit"] != "91b9c639bea60c114600aedd2f4f3fe97ec420e9":
        raise AssertionError("runtime visual behavioral baseline changed without explicit review")
    locked = contract["lockedInvariants"]
    if locked["d3d9exGameplayTransport"] != "DIRECT_GPU_ONLY":
        raise AssertionError("D3D9Ex gameplay transport contract must remain DirectGPU-only")
    if locked["desktopGameplayMirror"] != "MONO_OR_LEFT_EYE_NEVER_SBS":
        raise AssertionError("desktop gameplay mirror contract must forbid SBS")
    if locked["hudPresentation"] != "WORLD_FIXED_NOT_HEAD_LOCKED":
        raise AssertionError("HUD contract must remain world-fixed / not head-locked")
    required_build = contract["requiredActiveBuild"]
    if not required_build["r26HudCompare"] or required_build["variantId"] != "ACTIVE_R26_R43_R44":
        raise AssertionError("active build contract must keep the R26 + R43/R44 visual owner")

    require(".github/workflows/vr-dx9ex-active.yml", [
        "-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=ON",
        "ACTIVE_R26_R43_R44",
    ])
    forbid(".github/workflows/vr-dx9ex-active.yml", [
        "ACTIVE_FULL_R34",
        "-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=OFF -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF",
    ])
    require("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
        "R44OverlayOwnedWvpHits",
        "R30ScreenSpaceKind::PerspectiveHud",
        "GetLastRawGameWvpWrite",
        "R30BuildHudPlaneCoefficients",
        "R30XyzrhwWorldLockedHudDraws",
        "R47SemanticHudAccepted",
        "R47SemanticUnknownRejected",
        "GameSemantic::CorroboratesHud",
        "GameSemantic::CorroboratesWorld",
        "GameSemantic::ConsumeForDraw",
        "Never promote an unknown XYZRHW draw from D3D",
        "canonical EXE sprite-queue semantics own HUD transforms",
        "R48 final-test policy: screen/perspective HUD ownership comes only",
        "if (!semanticHud && !semanticWorld)",
        "The EXE queue semantic is the ownership proof",
    ])
    forbid("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp", [
        "if (state.depthTestEnabled && !state.worldEffect &&",
        "if (!state.worldEffect && !hudPlaneEvidence)",
        "r13FlatEffectShape",
        "if (zEnable != D3DZB_FALSE)",
    ])
    require("src/vr/game/render_semantics.hpp", [
        "RenderScope::ScreenHud",
        "RegisterSpriteNodeScope(",
        "ConsumeSpriteNodeScope(",
        "BeginSpriteQueueRender()",
        "SelectSpriteQueueNode(",
        "EndSpriteQueueRender()",
        "0x42D734",
        "0x42DCB4",
    ])
    require("src/hooks_uiscaling.cpp", [
        "VRHudQueueSemanticBridge",
        "Module::exe_ptr(0x2D734)",
        "Module::exe_ptr(0x2D762)",
        "Module::exe_ptr(0x2DCB4)",
        "RegisterSpriteNodeScope(",
        "RenderScope::WorldBillboard",
        "canonical sprite queue 0x2D734..0x2DCB4 owns SCREEN_HUD",
    ])
    require("src/vr/d3d9/stereo_renderer_r30.cpp", [
        "clipCorrection._11 = hudScaleX;",
        "const bool transformScissor = false;",
        "IDirect3DTexture9* compositeSource =",
        "compositeSource = R30SkyGlow.temp[eye];",
    ])
    forbid("src/vr/d3d9/stereo_renderer_r30.cpp", [
        "clipCorrection._11 = hudScaleX * eyeScale[eye];",
        "R30TransformHudScissor(savedScissor, savedViewport,",
    ])
    require("src/vr/d3d9/stereo_renderer_r31.cpp", [
        "screenKind != R30ScreenSpaceKind::Hud2D",
        "R30ClassifyScreenSpacePass(device) == R30ScreenSpaceKind::Hud2D",
    ])
    require("src/vr/game/outrun_renderer.cpp", [
        "CullingUnionFov disabled in active rendering after visual-regression evidence",
        "live projection remains untouched until a culling-only frustum boundary is proven",
    ])
    forbid("src/vr/game/outrun_renderer.cpp", [
        "two-eye union culling FOV ACTIVE",
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
    require("src/vr/d3d9/ex_device_upgrade.cpp", [
        "const DWORD dynamicUsage = usage | D3DUSAGE_DYNAMIC;",
        'dynamic ? "DEFAULT|DYNAMIC" : "DEFAULT fallback"',
        "CreateVertexBufferCompatHook.stdcall<HRESULT>(",
        "CreateIndexBufferCompatHook.stdcall<HRESULT>(",
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
        "RtlCaptureStackBackTrace(",
        "UIScaling-derived semantic ranges",
    ])
    require("src/hooks_textures.cpp", [
        "ApplyHudInspectorFeeds",
        "Settings::VREnabled && Settings::VRHudInspector",
        "Settings::UITextureReplacement || ApplyHudInspectorFeeds",
    ])
    require("tools/analyze_outrun_exe.py", [
        '0x02D0C0: "put_sprite_ex2"',
        '0x060900, 0x061100, "ctrl_icon_work", "HUD_CTRL_ICON"',
        '0x0BBA00, 0x0BBC00, "DispTempHeartNum", "HUD_TEMP_HEART"',
        '0x556C00: "sprite_prio_root"',
        "find_data_xrefs(pe)",
    ])
    require("src/vr/hud_semantics.hpp", [
        '"HUD_CTRL_ICON"',
        '"HUD_TEMP_HEART"',
        "0x060D40",
        "0x0BBA89",
    ])
    require("tools/Run-OutRunVRTest.ps1", [
        "LaunchConfigSha256",
        "OUTRUN_VR_EXE_SEMANTICS_VERIFIED",
        "Configuration identity is still inconsistent after session rotation.",
    ])
    profiles = read("tools/OutRunVR-TestProfiles.ps1")
    if "'-CullingUnionFov=false'" not in profiles:
        raise AssertionError("VR test profiles must keep union culling disabled until visually proven")
    if "'-DirectGpuOnly=true'" not in profiles:
        raise AssertionError("D3D9Ex VR test profiles must keep gameplay DirectGPU-only")
    if "'-DirectGpuOnly=false'" in profiles:
        raise AssertionError("SBS/Desktop-Duplication gameplay fallback must not be re-enabled by test profiles")
    correctness = profiles.split("Name='CORRECTNESS'", 1)[1]
    for marker in [
        "'-FramerateLimit=60'",
        "'-FramerateFastLoad=0'",
        "'-FramerateInterpolation=false'",
        "'-FramerateUnlockExperimental=false'",
        "'-FrameCadenceMode=0'",
        "'-DisableDesktopVsync=false'",
    ]:
        if marker not in correctness:
            raise AssertionError(
                f"CORRECTNESS profile missing conservative marker: {marker}")
    require("tools/Select-OutRunVRBackend.ps1", [
        '"d3d9-classic"',
        '"B_CLASSIC_D3D9_VR"',
        '"PreferD3D9Ex" "false"',
        "CLASSIC D3D9 VR",
    ])
    require("tools/Select-OutRunVRBackend.ps1", [
        'Set-IniSectionValue $text "VR" "DirectGpuOnly" "true"',
        "Never re-open ComposeSbs/Desktop-Duplication",
        "PC mirror remains mono/left-eye",
    ])
    require("tools/OutRunVR-Backend-Selector.ps1", [
        "CLASSIC D3D9 + VR",
        '"d3d9-classic"',
    ])
    require("vrhost/src/diagnostics/runtime_watchdog.cpp", [
        "VR_CAPTURE_LAST.txt",
        "status=CAPTURING",
        "status=READY",
        "MessageBeep(MB_OK)",
        "MessageBeep(MB_ICONASTERISK)",
    ])
    require("vrhost/src/main_r23.cpp", [
        '"outrun-vr-host-startup.log"',
        'startup("wait-game-window-begin")',
        'startup("shared-writer-ready")',
        'startup("compositor-ready")',
        'startup("fatal", e.what())',
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
        "FirstDeferredResourceInitLogged",
        "Resource creation is intentionally deferred beyond CreateDevice exposure.",
    ])
    forbid("src/vr/d3d9/stereo_renderer_r7.inc", [
        "private eye resources initialized only after first successful game Present",
    ])
    require("src/vr/d3d9/stereo_renderer_r23.cpp", [
        "R23 is the final effective Present owner in the layered hook chain.",
        "EnsureStereoResources(device)",
        "VR R23 INIT: private eye/backbuffer resources initialized after final game Present",
        "recovery baseline can now identify the main backbuffer",
    ])
    require("src/hooks_graphics.cpp", [
        "StockSkyGlowResourcesOwnedByGame()",
        "return !(Settings::VREnabled && Settings::VRStereo);",
        "MakeReduceBuff suppressed because Step1Tex is null",
        "EXE+0x14E87 null dereference",
    ])
    forbid("src/hooks_graphics.cpp", [
        "return Settings::SkyGlowFactor > 0 &&\n\t\t\t!OutRunVRStereo::IsRuntimeStereoActive();",
    ])
    graphics = read("src/hooks_graphics.cpp")
    if graphics.count("StockSkyGlowResourcesOwnedByGame()") < 3:
        raise AssertionError(
            "stock SkyGlow allocation and execution must share one ownership predicate")
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
