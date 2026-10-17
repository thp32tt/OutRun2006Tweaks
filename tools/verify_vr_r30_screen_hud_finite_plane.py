#!/usr/bin/env python3
"""Regression: source-owned R84 fixed-function gameplay HUD stays finite/paired.

This tests the compiled route and destructive variants. It does not assert
Quest3 correctness; head motion, optics and F11 require physical validation.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
r84 = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8-sig")
r26 = (root / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8-sig")
r29 = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8-sig")

def check(code: str) -> None:
    configure = code.split("bool R30ConfigureXyzrhwWorldEffect(", 1)[1].split(
        "// Smoke/sand can redraw a static VB/IB span", 1)[0]
    exact_result = "OutRunVR::GameSemantic::CanReprojectFiniteResultHudPlane("
    exact_hud = ("if (OutRunVR::GameSemantic::CorroboratesHud(\n"
                 "                    OutRunVR::GameSemantic::EffectiveScope()))")
    finite_plane = "R30BuildStageExtensionXyzrhwEyePlane("
    for required in (exact_result, exact_hud, finite_plane,
                     "state.projectedWorldMarker = true;",
                     "return haveBaseProjection &&"):
        assert required in configure, f"R84 HUD path missing {required}"
    assert configure.index("state.projectedWorldMarker = true;") < (
        configure.index(exact_result)) < configure.index(exact_hud)
    assert configure.index(exact_hud) < configure.index(
        "// Smoke/sand") if "// Smoke/sand" in configure else True
    fixed_hud = configure.split(exact_hud, 1)[1]
    assert fixed_hud.split("}", 1)[0].count(finite_plane) == 1
    assert "RenderScope::SkyGlow" not in fixed_hud
    assert "R30BuildStageExtensionXyzrhwEyePlane" in code
    stage = code.split("bool R30BuildStageExtensionXyzrhwEyePlane(", 1)[1].split(
        "bool R30XyzrhwHasProjectedDepthSignature(", 1)[0]
    assert "OutRunVRRenderer::GetLatchedHeadInverse(" in stage
    assert "headPoseSequence != state.stereo.poseSequence" in stage
    assert "state.stageExtensionClipFromGameNdc[eye] = result;" in stage
    assert "state.stageExtensionScale = hudScale;" in stage
    assert "state.stageExtensionEyePlane = true;" in stage
    assert "OutRunVR::StageExtensionPlane::ProjectPixelPair(" in code

assert "state.screenOverlay2D = semanticOverlay2D;" in r26
assert "RenderScope::ScreenHud" in r29
check(r84)
for old in (
    "OutRunVR::GameSemantic::CorroboratesHud(\n",
    "                    OutRunVR::GameSemantic::EffectiveScope()))",
    "return haveBaseProjection &&\n                    R30BuildStageExtensionXyzrhwEyePlane(\n",
):
    # Mutate only the newest ordinary ScreenHud block, not the earlier exact
    # producer +TIME/GOAL block, so missing ownership cannot be concealed.
    start = r84.index("// 2026-10-17 Quest R84:")
    part = r84[start:]
    assert old in part, f"mutation fixture absent {old}"
    changed = r84[:start] + part.replace(old, "REMOVED_REGRESSION_MARKER", 1)
    try:
        check(changed)
    except AssertionError:
        pass
    else:
        raise AssertionError(f"ordinary ScreenHud mutation survived: {old}")
print("PASS R84 source-owned XYZRHW ScreenHud finite bilateral plane; sky/particles/markers isolated; Quest3 UNTESTED")


# The same source-proven native ScreenHud / queued HUD screen pixels must
# use the ORIGINAL 2D viewport, not the physically larger OpenXR eye RT.
stage = r84.split("bool R30BuildStageExtensionXyzrhwEyePlane(", 1)[1].split(
    "bool R30XyzrhwHasProjectedDepthSignature(", 1)[0]
for token in ("nativeScreenHudPixels", "queuedOriginalHudPixels",
              "CorroboratesHud(", "QueueOverlayNeedsFiniteHudPlane(",
              "ExternalOverlaySemanticDepth != 0", "goalPresentationPixels",
              "state.stageSource2DWidth = gameWidth;",
              "state.stageSource2DHeight = gameHeight;"):
    assert token in stage, token
assert stage.index("nativeScreenHudPixels") < stage.index(
    "Game::screen_resolution")
vertices = r84.split("const bool gamePixelViewport =", 1)[1].split(
    "if (state.stageExtensionEyePlane)", 1)[0]
for token in ("state.stageSource2DWidth > 0.f",
              "state.stageSource2DHeight > 0.f",
              "const float sourceX0 =", "const float sourceY0 =",
              "const float sourceWidth =", "const float sourceHeight =",
              "R30GetExactHudEdgeAnchor("):
    assert token in vertices, token
draw = r84.split("if (state.stageExtensionEyePlane)", 1)[-1]
assert "sourceX, sourceY, sourceX0, sourceY0," in draw
assert "sourceWidth, sourceHeight," in draw
assert "ProjectPixelPairAcrossViewports(" in draw
for token in ("nativeScreenHudPixels ||", "queuedOriginalHudPixels) &&",
              "const float sourceWidth = gamePixelViewport"):
    mutated = r84.replace(token, "BROKEN_HUD_VIEWPORT_OWNER", 1)
    assert token not in mutated
    try:
        if token == "nativeScreenHudPixels ||":
            assert token in mutated.split(
                "bool R30BuildStageExtensionXyzrhwEyePlane(", 1)[1]
        elif token == "queuedOriginalHudPixels) &&":
            assert token in mutated.split(
                "bool R30BuildStageExtensionXyzrhwEyePlane(", 1)[1]
        else:
            assert token in mutated.split("const bool gamePixelViewport =", 1)[1]
    except AssertionError:
        pass
    else:
        raise AssertionError("game/source viewport negative mutation survived: " + token)
print("PASS R84 original game-pixel HUD to XR-eye viewport; native/queue/goal ownership and rollback negatives")
