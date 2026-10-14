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
    owned = renderer.split("HRESULT R30TryScreenSpaceFovDraw(", 1)[1].split("D3DVIEWPORT9 savedViewport", 1)[0]
    boundary = "if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(semanticScope))"
    assert boundary in owned
    assert owned.index(boundary) < owned.index("R30CaptureSkyGlowSceneBeforeHud(device);")
    assert owned.count("R30CaptureSkyGlowSceneBeforeHud(device);") == 1
    assert "R30CaptureSkyGlowSceneBeforeHud(device);\n\n            // From this point" not in owned

source=RENDER.read_text(encoding="utf-8")
semantic=SEMANTIC.read_text(encoding="utf-8")
check(source, semantic)
mutations=[
    (source.replace("if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(semanticScope))", "if (true)",1),semantic),
    (source.replace("!OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(scope)", "false",1),semantic),
    (source.replace("if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(semanticScope))\n                R30CaptureSkyGlowSceneBeforeHud(device);", "R30CaptureSkyGlowSceneBeforeHud(device);",1),semantic),
    (source,semantic.replace("scope == RenderScope::ScreenOverlay2D;", "scope == RenderScope::WorldBillboard;",1)),
]
for bad_r,bad_s in mutations:
    try:
        check(bad_r,bad_s)
    except (AssertionError,IndexError,ValueError):
        continue
    raise AssertionError("SkyGlow semantic boundary mutation escaped")
print("PASS R26+HUD SkyGlow screen cutoff, world lens preservation, 4 negative mutations")
