#!/usr/bin/env python3
"""Protect R26->R84 ESC source HUD restoration and fixed-function sky isolation.

This does NOT claim Quest 3 optical success. The independent original sky
sphere keeps R7's rotation-only projection while source-owned GUI never enters
the generic 3D sky heuristic.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R30=ROOT/"src/vr/d3d9/stereo_renderer_r30.cpp"
R7=ROOT/"src/vr/d3d9/stereo_renderer_r7.inc"
R26=ROOT/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
SEM=ROOT/"src/vr/game/render_semantics.hpp"

def check(r30, r7, r26, semantic):
    classify=r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(",1)[1].split(
        "struct R30EyeAffineCache",1)[0]
    assert "if (ownedOverlay)" in classify
    pause=classify.split("if (ownedOverlay)",1)[1].split(
        "// All other tagged overlays/effects",1)[0]
    for flag in ("R30IsPauseMenuElement()", "drawCommand.queued",
                 "drawCommand.queueNode", "drawCommand.queueEpoch != 0",
                 "R30ScreenSpaceKind::Hud2D", "R30ScreenSpaceKind::None"):
        assert flag in pause, "pause-only perspective shader owner: "+flag
    assert classify.index("if (ownedHud)") < classify.index("if (ownedOverlay)")
    assert "RenderScope::ScreenOverlay2D" in r30
    shader=r30.split("bool R30BuildScreenSpaceEyeConstants(",1)[1].split(
        "bool R30TryScreenSpaceFovDraw(",1)[0]
    assert "if (exactHud || genericQueuedHud)" in shader
    assert "R30GetRecentOriginalHudWvp(rawGameWvp)" in shader
    # Keep the live source-owned queue in the ESC optical plane only after
    # exact original WVP provenance; the former exactHud-only condition is
    # deliberately replaced by the shared paused source predicate.
    assert "const bool exactPauseShaderOwner =" in shader
    assert "OutRunVrPauseEye::OwnsPauseShaderPlane(" in shader
    assert "exactHud, genericQueuedHud, R30IsPauseMenuElement());" in shader
    assert shader.index("R30GetRecentOriginalHudWvp(rawGameWvp)") < shader.index(
        "OutRunVrPauseEye::OwnsPauseShaderPlane(")
    fixed=r30.split("HRESULT R30TryFixedFunctionOriginalSpriteStereo(",1)[1].split(
        "HRESULT R30TryXyzrhwIndexedPrimitiveVB(",1)[0]
    for flag in ("const bool pauseOverlay =", "sourceScope == RenderScope::ScreenOverlay2D",
                 "R30IsPauseMenuElement()", "pauseCommand.queued",
                 "pauseCommand.queueNode", "pauseCommand.queueEpoch != 0",
                 "fvf != 0x00000142u", "state.stageExtensionEyePlane",
                 "state.stageExtensionClipFromGameNdc[eye]",
                 "R30ExecuteXyzrhwStereo(", "R84/R62-FVF142-PauseOverlay",
                 "D3DTS_PROJECTION, &originalProjection"):
        assert flag in fixed, "pause fixed function stereo/restore: "+flag
    assert "R62TryFixedFunctionSpriteIndexed" in r26
    assert "R30ScreenSpaceKind::ScreenOverlay2D" in r26
    assert "OwnsGenericQueuedOverlay(provenance)" in r30
    assert "RenderScope::ScreenOverlay2D && queued && !external" in semantic
    # R7's depth-disabled fixedfn XYZ branch historically classified any
    # gameplay draw as a sky sphere, including ESC. Its source-owned screen
    # path must now veto this heuristic before the depth/projection test.
    r7fixed=r7.split("EyeBuildResult BuildEyeConstants(",1)[1].split(
        "float verifiedConstants[16]",1)[0]
    veto="CapturePhysicalDrawCommand()"
    assert veto in r7fixed and ".DeniesGenericWorldFallback()" in r7fixed
    assert r7fixed.index(veto) < r7fixed.index("ClassifyFixedFunctionStereo(")
    assert "FixedFunctionStereoPolicy::SkyRotationOnly" in r7fixed
    assert "if (rotationOnly)" in r7fixed
    assert "appliedHeadInverse._41 = 0.0f" in r7fixed
    assert "eyeOffset[0] = eyeOffset[1] = eyeOffset[2] = 0.0f" in r7fixed
    # R26's old DrawPrimitive/Indexed/UP pre-screen callback also covered
    # HUD routed back to native original Draw. R84 R33 must now stamp and
    # capture before the fallback, NOT only after a successful R30 eye draw.
    r33=(ROOT/"src/vr/d3d9/stereo_renderer_r33.cpp").read_text(
        encoding="utf-8-sig")
    api=(ROOT/"src/vr/core/r30_support_api.hpp").read_text(
        encoding="utf-8-sig")
    assert "R30SupportBeforeScreenDrawForSkyGlow(device," in r33
    assert r33.index("R30SupportBeforeScreenDrawForSkyGlow(device,") < (
        r33.index("if (!resyncAlreadyFlushed)",r33.index(
            "const auto drawCommand =",r33.index("HRESULT R33Dispatch("))))
    assert "IsSkyGlowPreHudBoundary(" in r33
    assert "void R30SupportBeforeScreenDrawForSkyGlow(" in api
    capture=r30.split("void R30SupportBeforeScreenDrawForSkyGlow(",1)[1].split(
        "R30SupportScreenSpaceKind R30SupportClassifyScreenSpacePass(",1)[0]
    for flag in ("R29OwnerIsGameDevice(device)",
                 "R29OwnerInternalStereoPassActive()",
                 "R29OwnerTargetIsBackBuffer()",
                 "R30SkyGlowScreenDrawEpoch == frame.presentEpoch",
                 "R30CaptureSkyGlowSceneBeforeHud(device)"):
        assert flag in capture
    sky=r30.split("bool R30ApplyStereoSkyGlow(",1)[1].split(
        "ULONGLONG R30LastTelemetryMs",1)[0]
    for flag in ("STATE_WARP","STATE_RESTART","STATE_GOAL",
                 "STATE_TIMEUP","STATE_LINK_TIMEUP","STATE_GIVEUP",
                 "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch",
                 "R30SkyGlowScreenDrawEpoch == frame.presentEpoch"):
        assert flag in sky
    assert "scope == RenderScope::SkyGlow" in semantic
    assert "scope == RenderScope::ScreenOverlay2D" in semantic
    return True

s=[p.read_text(encoding="utf-8-sig") for p in (R30,R7,R26,SEM)]
assert check(*s)
mutations=[
    (0,"drawCommand.queueEpoch != 0","false /* no queue generation */"),
    (0,"drawCommand.queueEpoch != 0\n                    ? R30ScreenSpaceKind::Hud2D",
     "drawCommand.queueEpoch != 0\n                    ? R30ScreenSpaceKind::None"),
    (0,"exactHud, genericQueuedHud, R30IsPauseMenuElement());",
     "exactHud, genericQueuedHud, true);"),
    (0,"OutRunVrPauseEye::OwnsPauseShaderPlane(",
     "OutRunVrPauseEye::WrongPauseShaderPlane("),
    (0,"pauseCommand.queueNode &&","true &&"),
    (0,"R84/R62-FVF142-PauseOverlay","R84/R62-FVF142-WorldSky"),
    (1,".DeniesGenericWorldFallback()",".IsDirectWorldLensCentre()"),
    (1,"appliedHeadInverse._41 = 0.0f","appliedHeadInverse._41 = 1.0f"),
]
for i,needle,bad in mutations:
    assert needle in s[i], f"negative fixture absent: {needle}"
    changed=s[:]
    changed[i]=changed[i].replace(needle,bad,1)
    try: check(*changed)
    except AssertionError: pass
    else: raise AssertionError(f"negative mutation escaped: {needle}")
print("PASS exact ESC 2D native/stereo vs genuine 3D sky; 6 negative mutations; HMD UNTESTED")
