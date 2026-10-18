#include "../../src/vr/game/render_semantics.hpp"
#include "../../src/vr/game/stage_extension_physical_source.hpp"
#include "../../src/vr/game/sprite_queue_tail_proof.hpp"
#include "../../src/vr/d3d9/lens_centre_relative_eye_pose.hpp"
#include <iostream>
#include <cmath>
#include <limits>

int main()
{
    using namespace OutRunVR::GameSemantic;
    // Physical +TIME GPU source: an original c64 write during LEFT must
    // quarantine RIGHT even when producer/queue/shader/pose stay unchanged.
    // Both direct numeric and queued sprite routes share this same guard.
    {
        using namespace OutRunVR::StageExtensionPhysical;
        Source direct{RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
            false, nullptr, 0, 7, 11, 0, 0, 41, 11};
        if (!IsValid(direct) || !SameAfterNativeLeft(direct, direct))
            return 94;
        Source changed = direct;
        ++changed.rawWvpWriteSerial;
        if (!IsValid(changed) || SameAfterNativeLeft(direct, changed))
            return 95; // original shader c64 changed during native LEFT
        changed = direct;
        ++changed.rawWvpDrawSerial;
        if (SameAfterNativeLeft(direct, changed))
            return 96; // original game draw generation also belongs to source
        changed = direct;
        changed.rawWvpDrawSerial = 0;
        if (IsValid(changed) || SameAfterNativeLeft(direct, changed))
            return 97; // partial raw WVP pair must never be admitted
        changed = direct;
        changed.rawWvpWriteSerial = 0;
        changed.rawWvpDrawSerial = 0;
        if (!IsValid(changed))
            return 98; // unavailable raw tracker keeps legacy safe fallback
        int first = 0, second = 0;
        Source queued = direct;
        queued.queued = true;
        queued.node = &first;
        queued.queueEpoch = 3;
        if (!IsValid(queued) || !SameAfterNativeLeft(queued, queued))
            return 99;
        changed = queued;
        changed.node = &second;
        if (SameAfterNativeLeft(queued, changed))
            return 100;
        changed = queued;
        changed.queueEpoch = 4;
        if (SameAfterNativeLeft(queued, changed))
            return 101;
        changed = queued;
        ++changed.rawWvpWriteSerial;
        if (SameAfterNativeLeft(queued, changed))
            return 102; // queued sprite cannot borrow another raw c64
        changed = queued;
        changed.producer = ProducerToken::GoalTime020;
        if (IsValid(changed) || SameAfterNativeLeft(queued, changed))
            return 103; // GOAL stays separate from +TIME
        changed = queued;
        changed.scope = RenderScope::WorldBillboard;
        if (IsValid(changed) || SameAfterNativeLeft(queued, changed))
            return 104; // world / lens cannot become a screen HUD
    }
    // The real sprite priority head uses itself as tail_4 when empty.
    // When +TIME is the first exact producer in that priority, retain ALL
    // of its appended sprite and numeric nodes, not just later siblings.
    // These exact-source tags are consumed by the live R84 HUD-eye route.
    {
        struct Node { Node* next_0 = nullptr; };
        Node root{}, firstGlyph{}, secondGlyph{}, stale{};
        root.next_0 = &firstGlyph;
        firstGlyph.next_0 = &secondGlyph;
        using OutRunVR::SpriteQueue::FirstVerifiedAppendedNode;
        if (FirstVerifiedAppendedNode(&root, &root, &secondGlyph, 2u)
                != &firstGlyph ||
            FirstVerifiedAppendedNode(&root, &root, &firstGlyph, 2u))
            return 90; // only the LIVE terminal tail proves a complete +TIME batch
        if (FirstVerifiedAppendedNode(&root, &root, &secondGlyph, 1u) ||
            FirstVerifiedAppendedNode(&root, &root, &stale, 2u) ||
            FirstVerifiedAppendedNode(&root, static_cast<Node*>(nullptr), &root, 2u) ||
            FirstVerifiedAppendedNode(&root, &root, &root, 2u))
            return 91; // truncated, stale and sentinel-as-data fail closed
        if (FirstVerifiedAppendedNode(&root, static_cast<Node*>(nullptr), &secondGlyph, 2u) ||
            FirstVerifiedAppendedNode(&root, &firstGlyph, &secondGlyph, 2u)
                != &secondGlyph)
            return 92; // null snapshot is unproven; real linked old tail still works
        root.next_0 = &secondGlyph;
        if (FirstVerifiedAppendedNode(&root, &firstGlyph, &secondGlyph, 2u))
            return 93; // detached prior tail must not tag foreign queue
    }
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
    // Direct numeric and queued +TIME may share the original semantic
    // token but must NOT share an owned native GPU batch. The physical
    // queue-node/epoch ledger distinguishes the sources, not the token.
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2u, true, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime, true));
    // A stale queued +TIME buffer with that same token is never drained as
    // direct work; it must follow its original queue/End fallback instead.
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2u, true, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime, false));
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

    // ESC option arrows use an exact deferred GPU source across original
    // direct E8 and queued SpriteNode submissions. Generic HUD/GOAL must
    // not be reclassified into the pause-menu optical path.
    constexpr auto pause = ProducerToken::PauseOptionArrow;
    if (!CanDrainDirectResultBeforeFirstQueueNode(false, true, true, 1u,
            true, hud, pause, hud, ProducerToken::ExactScreenHudClipSprite) ||
        !CanArmD3DXQueueGoalAfterDraw(true, true, true, 1u,
            true, hud, pause, hud, pause) ||
        !CanDeferD3DXQueueGoalBatch(true, true, true, true, 2u,
            true, hud, pause, hud, pause) ||
        !CanFlushD3DXDirectGoalAtExit(false, true, true, 2u,
            true, hud, pause, hud, pause) ||
        CanReprojectFiniteResultHudPlane(hud, pause) ||
        CanFlushD3DXDirectGoalAtExit(false, true, true, 1u,
            true, hud, ProducerToken::ExactScreenHudClipSprite,
            hud, ProducerToken::ExactScreenHudClipSprite) ||
        CanFlushD3DXDirectGoalAtExit(false, true, true, 1u,
            false, hud, pause, hud, pause) ||
        CanFlushD3DXDirectGoalAtExit(false, true, true, 1u,
            true, hud, pause, hud, ProducerToken::GoalTime020))
        return 16;

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
