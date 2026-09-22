#!/usr/bin/env python3
"""Fail CI if the runtime-proven R49 visual ownership stack is lost again."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(path: str, *markers: str) -> None:
    text = read(path)
    missing = [m for m in markers if m not in text]
    if missing:
        raise AssertionError(f"{path}: missing visual-contract markers: {missing}")

def forbid(path: str, *markers: str) -> None:
    text = read(path)
    present = [m for m in markers if m in text]
    if present:
        raise AssertionError(f"{path}: regressed visual-contract markers present: {present}")

def main() -> int:
    contract = json.loads(read("docs/VR_RUNTIME_VISUAL_CONTRACT.json"))
    locked = contract["lockedInvariants"]
    required = contract["requiredActiveBuild"]
    if locked["d3d9exGameplayTransport"] != "DIRECT_GPU_ONLY":
        raise AssertionError("visual contract requires DirectGPU-only D3D9Ex gameplay")
    if locked["desktopGameplayMirror"] != "MONO_OR_LEFT_EYE_NEVER_SBS":
        raise AssertionError("visual contract forbids SBS desktop gameplay fallback")
    if locked["hudPresentation"] != "WORLD_FIXED_NOT_HEAD_LOCKED":
        raise AssertionError("HUD visual contract changed")
    if not required["r26HudCompare"] or required["variantId"] != "ACTIVE_R26_R43_R44":
        raise AssertionError("active build no longer selects runtime-proven R26/R43/R44 owner")

    require(".github/workflows/vr-dx9ex-active.yml",
            "-DOUTRUN_VR_R26_HUD_COMPARE=ON",
            "ACTIVE_R26_R43_R44",
            "python tools/verify_vr_visual_contract.py")
    forbid(".github/workflows/vr-dx9ex-active.yml",
           "ACTIVE_FULL_R34",
           "-DOUTRUN_VR_R26_HUD_COMPARE=OFF")

    profiles = read("tools/OutRunVR-TestProfiles.ps1")
    require("tools/OutRunVR-TestProfiles.ps1",
            "$visualSafeVr",
            "'-DirectGpuOnly=true'",
            "'-CullingUnionFov=false'",
            "'-FramerateLimit=60'",
            "'-FramerateFastLoad=0'",
            "'-FramerateInterpolation=false'",
            "'-FramerateUnlockExperimental=false'",
            "'-FrameCadenceMode=0'",
            "'-DisableDesktopVsync=false'")
    correctness = profiles.split("Name='CORRECTNESS'", 1)[1]
    if ") + $visualSafeVr" not in correctness:
        raise AssertionError("CORRECTNESS no longer binds the R49 visual-safe runtime set")

    require("src/vr/game/render_semantics.hpp",
            "RenderScope::ScreenHud",
            "RegisterSpriteNodeScope(",
            "ConsumeSpriteNodeScope(",
            "BeginSpriteQueueRender()",
            "SelectSpriteQueueNode(",
            "EndSpriteQueueRender()",
            "0x42D734",
            "0x42DCB4")

    require("src/hooks_uiscaling.cpp",
            "VRHudQueueSemanticBridge",
            "Module::exe_ptr(0x2D734)",
            "Module::exe_ptr(0x2D762)",
            "Module::exe_ptr(0x2DCB4)",
            "RegisterSpriteNodeScope(",
            "RenderScope::WorldBillboard",
            "canonical sprite queue 0x2D734..0x2DCB4 owns SCREEN_HUD")

    require("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
            "R47SemanticHudAccepted",
            "R47SemanticUnknownRejected",
            "GameSemantic::CorroboratesHud",
            "GameSemantic::CorroboratesWorld",
            "GameSemantic::ConsumeForDraw",
            "canonical EXE sprite-queue semantics own HUD transforms",
            "if (!semanticHud && !semanticWorld)")
    forbid("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
           "if (state.depthTestEnabled && !state.worldEffect &&",
           "if (!state.worldEffect && !hudPlaneEvidence)",
           "r13FlatEffectShape",
           "if (zEnable != D3DZB_FALSE)")

    require("src/vr/d3d9/stereo_renderer_r30.cpp",
            "clipCorrection._11 = hudScaleX;",
            "const bool transformScissor = false;",
            "IDirect3DTexture9* compositeSource =",
            "compositeSource = R30SkyGlow.temp[eye];")
    forbid("src/vr/d3d9/stereo_renderer_r30.cpp",
           "clipCorrection._11 = hudScaleX * eyeScale[eye];",
           "R30TransformHudScissor(savedScissor, savedViewport,")

    require("src/vr/d3d9/stereo_renderer_r31.cpp",
            "screenKind != R30ScreenSpaceKind::Hud2D",
            "R30ClassifyScreenSpacePass(device) == R30ScreenSpaceKind::Hud2D")

    require("src/vr/game/outrun_renderer.cpp",
            "CullingUnionFov disabled in active rendering after visual-regression evidence",
            "live projection remains untouched until a culling-only frustum boundary is proven",
            "R49 final ownership split",
            "SemanticOverlayBypassCalls",
            "VR R49 HUD OWNER: semantic overlay c64 kept raw")
    forbid("src/vr/game/outrun_renderer.cpp",
           "two-eye union culling FOV ACTIVE")

    require("src/vr/debug/hud_inspector.cpp",
            "InspectorActive",
            "SemanticIdentityVerified",
            "OUTRUN_VR_EXE_SEMANTICS_VERIFIED",
            "RtlCaptureStackBackTrace(",
            "UIScaling-derived semantic ranges",
            "MakeKey(kind, callRva, arg0, arg1, mode, stage)")

    require("src/vr/hud_semantics.hpp",
            '"HUD_CTRL_ICON"',
            '"HUD_TEMP_HEART"',
            "0x060D40",
            "0x0BBA89")

    require("src/hooks_textures.cpp",
            "ApplyHudInspectorFeeds",
            "Settings::VREnabled && Settings::VRHudInspector",
            "Settings::UITextureReplacement || ApplyHudInspectorFeeds")

    require("src/vr/d3d9/stereo_renderer_r34.cpp",
            "device->TestCooperativeLevel()",
            "D3DERR_DEVICELOST",
            "D3DERR_DEVICENOTRESET",
            "R34LostDeviceBypasses")

    require("src/vr/d3d9/ex_device_upgrade.cpp",
            "const DWORD dynamicUsage = usage | D3DUSAGE_DYNAMIC;",
            "CreateVertexBufferCompatHook.stdcall<HRESULT>(",
            "CreateIndexBufferCompatHook.stdcall<HRESULT>(")

    require("src/hooks_graphics.cpp",
            "StockSkyGlowResourcesOwnedByGame()",
            "MakeReduceBuff suppressed because Step1Tex is null",
            "EXE+0x14E87 null dereference")

    print("R49-equivalent runtime visual contract verification passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
