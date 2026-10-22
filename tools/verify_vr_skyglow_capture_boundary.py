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


# Default PC Fast R26+HUD must match the already bounded R84
# SkyGlow capture/resource-generation invariant. Source-level contract only:
# no claim that a mid-Present reconfiguration occurred on Quest3.
def check_r26_generation(renderer: str) -> None:
    release = renderer.split("void R30ReleaseSkyGlowResources() noexcept", 1)[1].split(
        "bool R30CompilePixelShader(", 1)[0]
    present = renderer.split("bool R30ApplyStereoSkyGlow(", 1)[1].split(
        "ULONGLONG R30LastTelemetryMs", 1)[0]
    invalidation = "R30SkyGlowSceneCaptureEpoch = R30NoSkyGlowEpoch;"
    assert release.count(invalidation) == 1, "resource rebuild retained an old capture epoch"
    ensure = "if (!R30EnsureSkyGlowResources(device))"
    assert present.count(ensure) == 1
    guard = ("if (R30SkyGlowScreenDrawEpoch == PresentEpoch &&\n"
             "                R30SkyGlowSceneCaptureEpoch != PresentEpoch)")
    assert present.count(guard) == 1, "missing mid-epoch capture-generation veto"
    assert (present.index("if (R30SkyGlowSceneCaptureEpoch != PresentEpoch &&") <
            present.index(ensure) < present.index(guard) <
            present.index("device->CreateStateBlock(")), "check must follow resource ensure before GPU work"
    veto = present.split(guard, 1)[1].split("IDirect3DStateBlock9* stateBlock", 1)[0]
    assert "++R30SkyGlowUiCaptureSkips;" in veto
    assert "return true;" in veto, "optional bloom should fail closed without poisoning stereo"
    capture = renderer.split("bool R30CaptureSkyGlowSceneBeforeHud(", 1)[1].split(
        "bool R30ApplyStereoSkyGlow(", 1)[0]
    assert "if (ok)\n                R30SkyGlowSceneCaptureEpoch = PresentEpoch;" in capture
    assert "R30SkyGlowScreenDrawEpoch = PresentEpoch;" in capture
    assert "R30CaptureSkyGlowSceneBeforeHud(device);" in capture
    assert "R30SkyGlowScreenDrawEpoch = R30NoSkyGlowEpoch;" in renderer, "Reset boundary preserved"

check_r26_generation(source)
generation_mutations = [
    ("drop resource lifetime invalidation",
     source.replace(
        "            R30SkyGlowSceneCaptureEpoch = R30NoSkyGlowEpoch;\n        }\n\n        bool R30CompilePixelShader",
        "        }\n\n        bool R30CompilePixelShader", 1)),
    ("drop after-Ensure veto",
     source.replace(
        "if (R30SkyGlowScreenDrawEpoch == PresentEpoch &&\n"
        "                R30SkyGlowSceneCaptureEpoch != PresentEpoch)",
        "if (false)", 1)),
    ("accept stale capture generation",
     source.replace(
        "R30SkyGlowSceneCaptureEpoch != PresentEpoch)\n"
        "            {\n                ++R30SkyGlowUiCaptureSkips;",
        "R30SkyGlowSceneCaptureEpoch == PresentEpoch)\n"
        "            {\n                ++R30SkyGlowUiCaptureSkips;", 1)),
]
for label, mutation in generation_mutations:
    assert mutation != source, f"mutation fixture missing: {label}"
    try:
        check_r26_generation(mutation)
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError(f"R26 capture-generation mutation escaped: {label}")
print("PASS R26+HUD SkyGlow capture/reallocation fail-closed and 3 negative mutations; HMD UNTESTED")
