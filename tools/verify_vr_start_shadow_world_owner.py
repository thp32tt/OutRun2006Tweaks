#!/usr/bin/env python3
"""DX9Ex original car-base shadow direct world owner; mutation regression."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/hooks_graphics.cpp"
SEM = ROOT / "src/vr/game/render_semantics.hpp"
FLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def check(code, sem):
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
        "Settings::VREnabled &&\n\t\t\t\t!OutRunVR::GameSemantic::QueueRenderActive()",
        "? OutRunVR::GameSemantic::RenderScope::WorldParticle",
        ": OutRunVR::GameSemantic::RenderScope::None",
        "a1, a4 * Settings::CarBaseShadowOpacity, 0, -1",
        "Game::mxPopMatrix();",
    ):
        assert fragment in block, fragment
    exact = sem.split("class ScopedExactProducerSemantic final", 1)[1].split(
        "inline void RegisterSpriteNodeScope(", 1)[0]
    # Preserve P0 world RAII and the exact direct-world ownership together.
    import re
    assert re.search(
        r"ScopedExactProducerSemantic directWorld\(\s*"
        r"directWorldScope, nullptr, true\s*\);\s*"
        r"OutRunVR::GameSemantic::ScopedRenderSemantic semantic\(\s*"
        r"OutRunVR::GameSemantic::RenderScope::WorldParticle\s*\);\s*"
        r"Game::DrawObjectAlpha_Internal\(\s*a1,\s*"
        r"a4\s*\*\s*Settings::CarBaseShadowOpacity,\s*0,\s*-1\);",
        block, re.S,
    )
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


def verify_mutations(code, sem):
    probes = (
        ("ScopedExactProducerSemantic directWorld(", "ScopedRenderSemantic directWorld("),
        ("!OutRunVR::GameSemantic::QueueRenderActive()", "OutRunVR::GameSemantic::QueueRenderActive()"),
        ("Settings::VREnabled &&\n\t\t\t\t!", "Settings::VREnabled ||\n\t\t\t\t!"),
        ("? OutRunVR::GameSemantic::RenderScope::WorldParticle", "? OutRunVR::GameSemantic::RenderScope::ScreenHud"),
        ("0x69EB4", "0xBBBBB"),
        ("a1, a4 * Settings::CarBaseShadowOpacity, 0, -1", "a1, a4 * 2.0f, 0, -1"),
        ("Game::mxPopMatrix();", "// missing matrix unwind"),
        ("Game::DrawObjectAlpha_Internal(", "Game::IncorrectObjectDraw("),
        ("ScopedRenderSemantic semantic(", "ScopedRenderSemantic escaped("),
        ("directWorldScope, nullptr, true", "directWorldScope, nullptr, false"),
    )
    for original, mutant in probes:
        assert original in code, original
        try:
            check(code.replace(original, mutant, 1), sem)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("mutant escaped: " + original)
    for original, mutant in (
        ("savedPendingDraw_ = NextDrawScope;", "savedPendingDraw_ = RenderScope::None;"),
        ("NextDrawScope = savedPendingDraw_;", "NextDrawScope = RenderScope::None;"),
    ):
        assert original in sem, original
        try:
            check(code, sem.replace(original, mutant, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("semantic mutant escaped: " + original)


def model():
    # Existing EffectiveScope prioritizes stale explicit HUD queue tokens.
    def effective(current, queue):
        return queue if queue in ("ScreenHud", "WorldBillboard",
                                  "ProjectedWorldMarker2D") else current
    assert effective("WorldParticle", "ScreenHud") == "ScreenHud"
    assert effective("WorldParticle", None) == "WorldParticle"
    for active in ("ScreenHud", "WorldBillboard", "ProjectedWorldMarker2D"):
        assert effective("WorldParticle", active) == active  # active queue unchanged


def main():
    code = SRC.read_text(encoding="utf-8")
    sem = SEM.read_text(encoding="utf-8")
    flow = FLOW.read_text(encoding="utf-8")
    assert flow.count("tools/verify_vr_start_shadow_world_owner.py") == 2
    check(code, sem)
    verify_mutations(code, sem)
    model()
    print("car shadow original CALL/world-eye ownership: PASS; 12 negative mutations rejected")


if __name__ == "__main__":
    main()
