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
    std::cout << "DX9Ex stage +TIME direct/queued owner PASS\n";
    return 0;
}
