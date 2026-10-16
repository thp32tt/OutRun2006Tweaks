#!/usr/bin/env python3
"""DX9Ex original car-base shadow direct world owner; mutation regression."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/hooks_graphics.cpp"
SEM = ROOT / "src/vr/game/render_semantics.hpp"
SHADOW = ROOT / "src/vr/game/car_base_shadow_stereo.hpp"
FLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def check(code, sem, shadow):
    block = code.split("class RestoreCarBaseShadow : public Hook", 1)[1].split(
        "RestoreCarBaseShadow RestoreCarBaseShadow::instance;", 1)[0]
    for addr in ("0x69EB4", "0x6AC76", "0x6B766"):
        assert block.count(addr) == 1, addr
    assert block.count("Memory::VP::InjectHook(") == 3
    assert block.count("Game::DrawObjectAlpha_Internal(") == 1
    for fragment in (
        "Settings::CarBaseShadowOpacity <= 0.f",
        "Game::mxPushLoadMatrix(&car->matrix_B0);",
        "Game::mxTranslate(0.0f, 0.05f, 0.0f);",
        "ScopedRenderSemantic semantic(",
        "ScopedExactProducerSemantic directWorld(",
        "directWorldScope, nullptr, true",
        "ProducerToken::CarBaseShadow",
        "Settings::VREnabled &&\n\t\t\t\t!OutRunVR::GameSemantic::QueueRenderActive()",
        "? OutRunVR::GameSemantic::RenderScope::WorldParticle",
        ": OutRunVR::GameSemantic::RenderScope::None",
        "float shadowAlpha = 0.f;",
        "OutRunVR::CarShadowStereo::ValidScaledAlpha(",
        "Settings::CarBaseShadowOpacity.get(), shadowAlpha",
        "a1, shadowAlpha, 0, -1",
        "Game::mxPopMatrix();",
    ):
        assert fragment in block, fragment
    exact = sem.split("class ScopedExactProducerSemantic final", 1)[1].split(
        "inline void RegisterSpriteNodeScope(", 1)[0]
    # Preserve P0 world RAII and the exact direct-world ownership together.
    import re
    assert re.search(
        r"ScopedExactProducerSemantic directWorld\(\s*"
        r"directWorldScope, nullptr, true,\s*"
        r"OutRunVR::GameSemantic::ProducerToken::CarBaseShadow\s*\);\s*"
        r"OutRunVR::GameSemantic::ScopedRenderSemantic semantic\(\s*"
        r"OutRunVR::GameSemantic::RenderScope::WorldParticle\s*\);\s*"
        r"Game::DrawObjectAlpha_Internal\(\s*a1,\s*"
        r"shadowAlpha\s*,\s*0,\s*-1\);",
        block, re.S,
    )
    assert block.index("ValidScaledAlpha(") < block.index(
        "Game::mxPushLoadMatrix(&car->matrix_B0);")
    assert "if (!OutRunVR::CarShadowStereo::ValidScaledAlpha(" in block
    owned = shadow.split("inline bool ValidScaledAlpha(", 1)[1].split(
        "struct DirectGameWvpOwner", 1)[0]
    for token in ("std::isfinite(raw)", "std::isfinite(opacity)",
                  "opacity <= 0.f", "raw * opacity",
                  "std::isfinite(candidate)", "out = candidate;"):
        assert token in owned, token

    for fragment in (
        "SpriteQueueDepth == 0", "savedQueueScope_ = CurrentQueueExactScope;",
        "CurrentQueueExactScope = RenderScope::None;",
        "CurrentQueueExactScope = savedQueueScope_;",
        "CurrentScope = savedScope_;",
        "CurrentQueueProjectedMarker = savedProjectedMarker_;",
        "isolatePendingDraw_(active_ && isolatePendingDraw)",
        "savedPendingDraw_ = NextDrawScope;",
        "NextDrawScope = RenderScope::None;",
        "NextDrawScope = savedPendingDraw_;",
    ):
        assert fragment in exact, fragment


def verify_mutations(code, sem, shadow):
    probes = (
        ("ScopedExactProducerSemantic directWorld(", "ScopedRenderSemantic directWorld("),
        ("!OutRunVR::GameSemantic::QueueRenderActive()", "OutRunVR::GameSemantic::QueueRenderActive()"),
        ("Settings::VREnabled &&\n\t\t\t\t!", "Settings::VREnabled ||\n\t\t\t\t!"),
        ("? OutRunVR::GameSemantic::RenderScope::WorldParticle", "? OutRunVR::GameSemantic::RenderScope::ScreenHud"),
        ("0x69EB4", "0xBBBBB"),
        ("a1, shadowAlpha, 0, -1", "a1, a4, 0, -1"),
        ("!OutRunVR::CarShadowStereo::ValidScaledAlpha(", "!OutRunVR::CarShadowStereo::InvalidScaledAlpha("),
        ("Game::mxPopMatrix();", "// missing matrix unwind"),
        ("Game::DrawObjectAlpha_Internal(", "Game::IncorrectObjectDraw("),
        ("ScopedRenderSemantic semantic(", "ScopedRenderSemantic escaped("),
        ("directWorldScope, nullptr, true", "directWorldScope, nullptr, false"),
        ("ProducerToken::CarBaseShadow", "ProducerToken::None"),
    )
    for original, mutant in probes:
        assert original in code, original
        try:
            check(code.replace(original, mutant, 1), sem, shadow)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("mutant escaped: " + original)
    for original, mutant in (
        ("savedPendingDraw_ = NextDrawScope;", "savedPendingDraw_ = RenderScope::None;"),
        ("NextDrawScope = savedPendingDraw_;", "NextDrawScope = RenderScope::None;"),
    ):
        assert original in sem, original
        try:
            check(code, sem.replace(original, mutant, 1), shadow)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("semantic mutant escaped: " + original)
    for original, mutant in (
        ("if (!std::isfinite(candidate))", "if (false)"),
        ("out = candidate;", "out = raw;"),
        ("opacity <= 0.f", "opacity < 0.f"),
    ):
        assert original in shadow, original
        try:
            check(code, sem, shadow.replace(original, mutant, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("unsafe alpha mutant escaped: " + original)


def model():
    # Existing EffectiveScope prioritizes stale explicit HUD queue tokens.
    def effective(current, queue):
        return queue if queue in ("ScreenHud", "WorldBillboard",
                                  "ProjectedWorldMarker2D") else current
    assert effective("WorldParticle", "ScreenHud") == "ScreenHud"
    assert effective("WorldParticle", None) == "WorldParticle"
    for active in ("ScreenHud", "WorldBillboard", "ProjectedWorldMarker2D"):
        assert effective("WorldParticle", active) == active  # active queue unchanged


def check_r84_shadow_route(semantic, r30, r32, r33, support, review):
    assert "return !IsDirectWorldLensCentre() &&\n                !IsDirectCarBaseShadow();" in semantic
    assert "static_assert(!PhysicalDrawCommand{RenderScope::WorldParticle" in semantic
    assert '#include "../game/car_base_shadow_stereo.hpp"' in r30
    classification = r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[1].split(
        "GetRendererProjectionSignature(m34, m44)", 1)[0]
    assert "if (drawCommand.IsDirectCarBaseShadow())" in classification
    assert "R30HasExactCarBaseShadowRawWvp(rawShadow)" in classification
    assert "R30ScreenSpaceKind::ExactCarBaseShadowWorld" in classification
    proof = r30.split("bool R30HasExactCarBaseShadowRawWvp(", 1)[1].split(
        "// Exact Calc3D2D rank", 1)[0]
    for s in ("drawCommand.IsDirectCarBaseShadow()",
              "GetLastRawGameWvpWrite(", "GetLastGameWvpSemanticProvenance(",
              "R29OwnerCurrentShaderEpoch(", "OwnsDirectGameWvp({",
              "GetCurrentLatchedPoseEpoch()", "GetLastGameWvpPoseEpoch()",
              "R29OwnerTopLevelDrawSerial() + 1u", "sourceScope, sourceProducer, queueNode, queueEpoch"):
        assert s in proof, s
    eye = r30.split("if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld ||", 1)[1].split(
        "if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect)", 1)[0]
    for s in ("ExactCarBaseShadowWorld", "R30HasExactCarBaseShadowRawWvp(rawGameWvp)",
              "R29OwnerMultiplyMatrix(stockRawWvp,", "R29OwnerMultiplyMatrix(worldView, headInverse)",
              "R29OwnerProjectionFromFov(baseProjection,",
              "viewDepth < (exactShadow ? 0.05f : 1.25f)"):
        assert s in eye, s
    for s in ("ExactCarBaseShadowWorld",):
        assert s in r32 and s in support and s in review
    physical = r33.split("R32ReviewOwnedResult R33TryHud(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR33(", 1)[0]
    for s in ("drawCommand.IsDirectCarBaseShadow()", "directCarShadow ||",
              "screenKind == R32ReviewScreenSpaceKind::ExactCarBaseShadowWorld",
              "if (directCarShadow && !provenCarShadowStereo)",
              "(directCarShadow && !hud.handled)",
              "return actualDraw();"):
        assert s in physical, s
    # Real producer->raw-c64->R84 physical Draw path, not a new token/enum-only
    # assertion. Mutating any independent source proof or fallback must fail.
    for before, after in (
        ("!IsDirectCarBaseShadow();", "true;"),
        ("R30HasExactCarBaseShadowRawWvp(rawShadow)", "true"),
        ("OwnsDirectGameWvp({", "false /*bypass*/ && OwnsDirectGameWvp({"),
        ("(directCarShadow && !hud.handled)", "false"),
    ):
        sources = [semantic, r30, r33]
        owner = next(i for i, source in enumerate(sources) if before in source)
        altered = sources.copy()
        altered[owner] = altered[owner].replace(before, after, 1)
        try:
            check_r84_shadow_route_shape(*altered, r32, support, review)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("R84 shadow route mutant escaped: " + before)


def check_r84_shadow_route_shape(semantic, r30, r33, r32, support, review):
    assert "return !IsDirectWorldLensCentre() &&\n                !IsDirectCarBaseShadow();" in semantic
    assert "R30HasExactCarBaseShadowRawWvp(rawShadow)" in r30
    assert "return OutRunVR::CarShadowStereo::OwnsDirectGameWvp({" in r30
    assert "(directCarShadow && !hud.handled)" in r33
    assert "if (directCarShadow && !provenCarShadowStereo)" in r33
    assert all("ExactCarBaseShadowWorld" in x for x in (r30, r32, support, review))


def main():
    code = SRC.read_text(encoding="utf-8")
    sem = SEM.read_text(encoding="utf-8")
    shadow = SHADOW.read_text(encoding="utf-8")
    flow = FLOW.read_text(encoding="utf-8")
    assert flow.count("tools/verify_vr_start_shadow_world_owner.py") == 2
    check(code, sem, shadow)
    verify_mutations(code, sem, shadow)
    model()
    r30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    r32 = (ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
    r33 = (ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
    support = (ROOT / "src/vr/core/r30_support_api.hpp").read_text(encoding="utf-8")
    review = (ROOT / "src/vr/core/r32_review_api.hpp").read_text(encoding="utf-8")
    check_r84_shadow_route(sem, r30, r32, r33, support, review)
    print("car shadow original CALL/world-eye ownership and R84 physical stereo route: PASS; fail-closed source/eye/native fallback")


if __name__ == "__main__":
    main()