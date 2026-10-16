#include "../../src/vr/game/render_semantics.hpp"
#include "../../src/vr/d3d9/lens_centre_relative_eye_pose.hpp"
#include <iostream>
#include <cmath>
#include <limits>

int main()
{
    using namespace OutRunVR::GameSemantic;
    // R84 +TIME/GOAL shared eye-plane: symmetric IPD is preserved, even
    // when the game receives very large but still finite tracking origins.
    // Before this source repair, float(left+right) overflowed to infinity,
    // making the finite result HUD-plane fail and fall back to mono/headlock.
    const float normal[2][3]{
        {-0.032f, 0.4f, -1.2f}, {0.032f, 0.4f, -1.2f}
    };
    float relative[2][3]{};
    if (!OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
            normal, relative) ||
        std::fabs(relative[0][0] + 0.032f) > 1.0e-6f ||
        std::fabs(relative[1][0] - 0.032f) > 1.0e-6f ||
        std::fabs(relative[0][1]) > 1.0e-6f ||
        std::fabs(relative[1][2]) > 1.0e-6f)
        return 12;
    const float large = (std::numeric_limits<float>::max)();
    const float distant[2][3]{
        {large, large, large}, {large, large, large}
    };
    if (!OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
            distant, relative))
        return 13;
    for (int eye = 0; eye < 2; ++eye)
        for (int axis = 0; axis < 3; ++axis)
            if (!std::isfinite(relative[eye][axis]) ||
                relative[eye][axis] != 0.0f)
                return 14;
    // A poisoned right-eye pose must never partially overwrite the last
    // stable stereo pair, nor authorize a new GPU-eye projection.
    float invalid[2][3]{
        {0.0f, 0.0f, 0.0f},
        {0.06f, std::numeric_limits<float>::quiet_NaN(), 0.0f}
    };
    if (OutRunVR::LensCentre::BuildHeadRelativeEyeOffsets(
            invalid, relative))
        return 15;
    for (int eye = 0; eye < 2; ++eye)
        for (int axis = 0; axis < 3; ++axis)
            if (relative[eye][axis] != 0.0f)
                return 16;
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
    // An unowned None/None D3DX batch must keep native End fallback.
    // This used to assert true; the source now correctly fails closed.
    static_assert(!CanFlushD3DXPreQueueStageBatch(
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
    // A direct +TIME/GOAL batch must physically flush under its saved owner
    // BEFORE the first foreign queued sprite, but never if it is mixed,
    // detached from the live D3DXSprite, or owned by an unknown source.
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2u, true, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 1u, true, RenderScope::ScreenHud,
        ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2u, true, RenderScope::ScreenHud,
        ProducerToken::None, RenderScope::ScreenOverlay2D,
        ProducerToken::StageExtensionTime));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2u, false, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, false, 2u, true, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2u, true, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 1u, true, RenderScope::ScreenHud,
        ProducerToken::ResultTextB9200,
        RenderScope::ScreenOverlay2D, ProducerToken::None));

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
    // The next foreign D3DX Draw can implicitly submit the previous
    // +TIME/GOAL texture batch. Its physical Flush must temporarily use
    // the outgoing ScreenHud producer and restore the incoming game's
    // world/overlay cursor and pending one-shot scope afterwards.
    CurrentScope = RenderScope::ScreenOverlay2D;
    CurrentQueueExactScope = RenderScope::None;
    CurrentDirectExactProducer = ProducerToken::None;
    NextDrawScope = RenderScope::WorldParticle;
    for (const ProducerToken prior : {
             ProducerToken::StageExtensionTime, ProducerToken::GoalTime020,
             ProducerToken::GoalTime150, ProducerToken::ResultProgress })
    {
        {
            ScopedExactProducerSemantic outgoingBatch(
                RenderScope::ScreenHud, nullptr, true, prior);
            if (EffectiveScope() != RenderScope::ScreenHud ||
                CurrentRenderProducerToken() != prior ||
                ConsumeForDraw() != RenderScope::ScreenHud)
                return 8;
        }
        if (CurrentScope != RenderScope::ScreenOverlay2D ||
            CurrentRenderProducerToken() != ProducerToken::None ||
            CurrentQueueExactScope != RenderScope::None ||
            NextDrawScope != RenderScope::WorldParticle)
            return 9;
    }
    NextDrawScope = RenderScope::None;
    // A live queue remains authoritative: direct outgoing owner rebinding
    // must neither steal the queue's +TIME tag nor its drawing cursor.
    SpriteQueueDepth = 1;
    CurrentScope = RenderScope::ScreenHud;
    CurrentQueueExactScope = RenderScope::ScreenHud;
    CurrentSpriteQueueProducer = ProducerToken::StageExtensionTime;
    {
        ScopedExactProducerSemantic outgoingBatch(
            RenderScope::ScreenHud, nullptr, true,
            ProducerToken::GoalTime020);
        if (CurrentRenderProducerToken() !=
                ProducerToken::StageExtensionTime ||
            EffectiveScope() != RenderScope::ScreenHud)
            return 10;
    }
    if (CurrentRenderProducerToken() != ProducerToken::StageExtensionTime)
        return 11;
    SpriteQueueDepth = 0;
    CurrentSpriteQueueProducer = ProducerToken::None;
    CurrentQueueExactScope = RenderScope::None;
    CurrentScope = RenderScope::None;

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
