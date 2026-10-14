#include "../../src/vr/game/render_semantics.hpp"
#include <iostream>

int main()
{
    using namespace OutRunVR::GameSemantic;
    // A queued world Draw may be armed before the original +TIME parent.
    CurrentScope = RenderScope::SceneEffect;
    CurrentQueueExactScope = RenderScope::WorldBillboard;
    NextDrawScope = RenderScope::WorldBillboard;
    CurrentDirectExactProducer = ProducerToken::RivalMarkerSprani;
    {
        ScopedExactProducerSemantic direct(
            RenderScope::ScreenHud, nullptr, true,
            ProducerToken::StageExtensionTime);
        if (CurrentScope != RenderScope::ScreenHud ||
            CurrentQueueExactScope != RenderScope::None ||
            NextDrawScope != RenderScope::None ||
            CurrentDirectExactProducer != ProducerToken::StageExtensionTime ||
            ConsumeForDraw() != RenderScope::ScreenHud)
            return 1;
    }
    if (CurrentScope != RenderScope::SceneEffect ||
        CurrentQueueExactScope != RenderScope::WorldBillboard ||
        NextDrawScope != RenderScope::WorldBillboard ||
        CurrentDirectExactProducer != ProducerToken::RivalMarkerSprani ||
        ConsumeForDraw() != RenderScope::WorldBillboard)
        return 2;

    // A reentrant producer inside a real SpriteNode renderer cannot steal
    // ownership from the live queue, even when the source parent is exact.
    SpriteQueueDepth = 1;
    CurrentScope = RenderScope::WorldParticle;
    CurrentQueueExactScope = RenderScope::WorldBillboard;
    CurrentDirectExactProducer = ProducerToken::None;
    NextDrawScope = RenderScope::SceneEffect;
    {
        ScopedExactProducerSemantic nested(
            RenderScope::ScreenHud, nullptr, true,
            ProducerToken::StageExtensionTime);
        if (CurrentScope != RenderScope::WorldParticle ||
            CurrentQueueExactScope != RenderScope::WorldBillboard ||
            CurrentDirectExactProducer != ProducerToken::None ||
            NextDrawScope != RenderScope::SceneEffect)
            return 3;
    }
    if (NextDrawScope != RenderScope::SceneEffect)
        return 4;
    SpriteQueueDepth = 0;
    CurrentQueueExactScope = RenderScope::None;
    NextDrawScope = RenderScope::None;
    // Used verbatim by the live D3DX hook; test old-owner-first before
    // first +TIME queue, old queued owner, and all negative admissions.
    static_assert(CanFlushD3DXPreQueueStageBatch(
        false, true, true, RenderScope::ScreenOverlay2D, ProducerToken::None,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(CanFlushD3DXPreQueueStageBatch(
        true, false, true, RenderScope::WorldBillboard,
        ProducerToken::RankMarkerSprani, RenderScope::WorldBillboard,
        ProducerToken::RankMarkerSprani));
    static_assert(!CanFlushD3DXPreQueueStageBatch(
        false, false, true, RenderScope::ScreenOverlay2D, ProducerToken::None,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanFlushD3DXPreQueueStageBatch(
        false, true, false, RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanFlushD3DXPreQueueStageBatch(
        false, true, true, RenderScope::SceneEffect, ProducerToken::None,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanFlushD3DXPreQueueStageBatch(
        false, true, true, RenderScope::ScreenOverlay2D, ProducerToken::None,
        RenderScope::ScreenOverlay2D, ProducerToken::StageExtensionTime));
    // A deferred Draw may still remain when the numeric E8 parent returns.
    // Only the same homogeneous +TIME source may submit before RAII restore.
    auto exactExit = [](bool queued, bool active, bool sprite,
                        unsigned draws, bool homogeneous,
                        RenderScope pendingScope, ProducerToken pendingSource,
                        RenderScope currentScope, ProducerToken currentSource) {
        return CanFlushD3DXDirectStageAtExit(
            queued, active, sprite, draws, homogeneous,
            pendingScope, pendingSource, currentScope, currentSource);
    };
    const auto hud = RenderScope::ScreenHud;
    const auto stage = ProducerToken::StageExtensionTime;
    if (!exactExit(false, true, true, 2, true, hud, stage, hud, stage))
        return 5;
    if (exactExit(true, true, true, 2, true, hud, stage, hud, stage) ||
        exactExit(false, false, true, 2, true, hud, stage, hud, stage) ||
        exactExit(false, true, false, 2, true, hud, stage, hud, stage) ||
        exactExit(false, true, true, 0, true, hud, stage, hud, stage) ||
        exactExit(false, true, true, 2, false, hud, stage, hud, stage) ||
        exactExit(false, true, true, 2, true, hud, stage,
                  RenderScope::WorldBillboard, stage) ||
        exactExit(false, true, true, 2, true, hud, stage, hud,
                  ProducerToken::GoalTime020) ||
        exactExit(false, true, true, 2, true, hud,
                  ProducerToken::GoalTime020, hud, stage))
        return 6;
    // Source-order regression: the exact C993 sun and other world/scene
    // effects must stay eligible for SkyGlow before the HUD cutoff, while
    // both direct +TIME glyphs and generic 2D queue overlays set the cutoff.
    if (!IsSkyGlowPreHudBoundary(RenderScope::ScreenHud) ||
        !IsSkyGlowPreHudBoundary(RenderScope::ScreenOverlay2D) ||
        IsSkyGlowPreHudBoundary(RenderScope::WorldBillboard) ||
        IsSkyGlowPreHudBoundary(RenderScope::WorldParticle) ||
        IsSkyGlowPreHudBoundary(RenderScope::SceneEffect) ||
        IsSkyGlowPreHudBoundary(RenderScope::ProjectedWorldMarker2D) ||
        IsSkyGlowPreHudBoundary(RenderScope::ProjectedScreenEffect2D) ||
        IsSkyGlowPreHudBoundary(RenderScope::SkyGlow) ||
        IsSkyGlowPreHudBoundary(RenderScope::None))
        return 7;
    std::cout << "DX9Ex stage +TIME direct/queued owner and SkyGlow UI cutoff PASS\n";
    return 0;
}
