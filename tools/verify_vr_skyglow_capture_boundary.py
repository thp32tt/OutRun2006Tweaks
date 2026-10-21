#!/usr/bin/env python3
"""R26+HUD delivered DLL: WorldBillboard must not freeze pre-HUD SkyGlow.

Mutation checks exercise both outer/delegated and owned-per-eye paths. This
is source-path validation, not optical Quest3/VDXR evidence.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
SEMANTIC = ROOT / "src/vr/game/render_semantics.hpp"

def check(renderer: str, semantic: str) -> None:
    assert "constexpr bool IsSkyGlowPreHudBoundary(RenderScope scope)" in semantic
    sem = semantic.split("constexpr bool IsSkyGlowPreHudBoundary(RenderScope scope)", 1)[1].split("static_assert", 1)[0]
    assert "scope == RenderScope::ScreenHud" in sem
    assert "scope == RenderScope::ScreenOverlay2D" in sem
    assert "WorldBillboard" not in sem and "SceneEffect" not in sem
    outer = renderer.split("void R30BeforeScreenDrawForSkyGlow(", 1)[1].split("bool R30ApplyStereoSkyGlow(", 1)[0]
    assert "!OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(scope)" in outer
    assert "R30SkyGlowScreenDrawEpoch = PresentEpoch;" in outer
    assert "R30CaptureSkyGlowSceneBeforeHud(device);" in outer
    owned = renderer.split("HRESULT R30TryScreenSpaceFovDraw(", 1)[1].split("// From this point the draw is owned by R30.", 1)[0]
    boundary = "if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(semanticScope))"
    assert boundary in owned
    assert owned.index(boundary) < owned.index("R30CaptureSkyGlowSceneBeforeHud(device);")
    assert owned.count("R30CaptureSkyGlowSceneBeforeHud(device);") == 1
    assert owned.count(boundary) == 1  # forbid duplicate or unrelated ownership gates

source=RENDER.read_text(encoding="utf-8")
semantic=SEMANTIC.read_text(encoding="utf-8")
check(source, semantic)
mutations=[
    (source.replace("if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(semanticScope))", "if (true)",1),semantic),
    (source.replace("!OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(scope)", "false",1),semantic),
    (source.replace("if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(semanticScope))\n                R30CaptureSkyGlowSceneBeforeHud(device);", "R30CaptureSkyGlowSceneBeforeHud(device);",1),semantic),
    (source,semantic.replace("return scope == RenderScope::ScreenHud ||\n            scope == RenderScope::ScreenOverlay2D;", "return scope == RenderScope::ScreenHud ||\n            scope == RenderScope::WorldBillboard;",1)),
]
for bad_r,bad_s in mutations:
    try:
        check(bad_r,bad_s)
    except (AssertionError,IndexError,ValueError):
        continue
    raise AssertionError("SkyGlow semantic boundary mutation escaped")
print("PASS R26+HUD SkyGlow screen cutoff, world lens preservation, 4 negative mutations")


# R84 main must preserve the same pre-HUD bloom ownership as R26+HUD.
# This checks the two R84 draw paths directly: screen-space shader and
# XYZRHW stereo. A world lens may never freeze the source early.
R84_RENDER = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
r84 = R84_RENDER.read_text(encoding="utf-8")

def check_r84(renderer: str) -> None:
    fov = renderer.split("HRESULT R30TryScreenSpaceFovDraw(", 1)[1].split("// From this point the draw is owned by R30.", 1)[0]
    xyz = renderer.split("HRESULT R30ExecuteXyzrhwStereo(", 1)[1].split("R29OwnerNoteStereoDrawWithoutMonoBackup()", 1)[0]
    boundary = "OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary("
    scope = "OutRunVR::GameSemantic::EffectiveScope()"
    capture = "R30CaptureSkyGlowSceneBeforeHud(device);"
    assert fov.count(boundary) == 1 and fov.count(scope) == 1 and fov.count(capture) == 1
    assert fov.index(boundary) < fov.index(capture)
    assert xyz.count(boundary) == 1 and xyz.count(scope) == 1 and xyz.count(capture) == 1
    assert xyz.index("!state.worldEffect") < xyz.index(boundary) < xyz.index(capture)

check_r84(r84)
bad_variants = [
    r84.replace("if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(\n                    OutRunVR::GameSemantic::EffectiveScope()))", "if (true)", 1),
    r84.replace("if (!state.worldEffect &&\n                OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(", "if (!state.worldEffect &&\n                true /* unsafe bloom */ && (", 1),
    r84.replace("if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(\n                    OutRunVR::GameSemantic::EffectiveScope()))\n                R30CaptureSkyGlowSceneBeforeHud(device);", "R30CaptureSkyGlowSceneBeforeHud(device);", 1),
]
for mutated in bad_variants:
    assert mutated != r84, "R84 bloom mutation fixture missing"
    try:
        check_r84(mutated)
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError("R84 pre-HUD SkyGlow mutation escaped")
print("PASS R84 main SkyGlow screen-only cutoff and three negative mutations; HMD UNTESTED")

# Isolated DX9Ex review105 integration guard. These are source-level
# invariants; a Windows compile and a Quest3 optical A/B are separate gates.
def check_review105_patch(renderer: str) -> None:
    sky = renderer.split("bool R30DrawSkyGlowPass(", 1)[1].split(
        "bool R30CaptureSkyGlowSceneBeforeHud(", 1)[0]
    assert sky.index("device->SetViewport(&viewport)") < sky.index(
        "D3DRS_SCISSORTESTENABLE, FALSE"
    ) < sky.index("device->DrawPrimitiveUP(")
    overlay = renderer.split("bool R30BuildHudPlaneCoefficients(", 1)[1].split(
        "bool R30ExternalImGuiIdentity(", 1)[0]
    assert "bool screenOverlay2D = false" in overlay
    assert "if (screenOverlay2D)" in overlay
    assert "scaleX = R30HudScaleValue();" in overlay
    assert "R30HudContainScale(state.stereo, scaleX, scaleY);" in overlay
    assert "state, true, semanticOverlay2D" in renderer

check_review105_patch(source)
for replacement in (
    source.replace("D3DRS_SCISSORTESTENABLE, FALSE", "D3DRS_SCISSORTESTENABLE, TRUE", 1),
    source.replace("state, true, semanticOverlay2D", "state, true, false", 1),
):
    try:
        check_review105_patch(replacement)
    except (AssertionError, IndexError, ValueError):
        pass
    else:
        raise AssertionError("DX9Ex review105 regression mutation escaped")
print("PASS R26 SkyGlow target-scissor and ScreenOverlay2D scalar route; HMD UNTESTED")
