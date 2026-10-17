#include "../../src/vr/game/render_semantics.hpp"
#include "../../src/vr/game/goal_result_parent_provenance.hpp"
#include <iostream>

using namespace OutRunVR::GameSemantic;

static bool CheckDirectGoal(ProducerToken token)
{
    CurrentScope = RenderScope::SceneEffect;
    CurrentQueueExactScope = RenderScope::WorldBillboard;
    NextDrawScope = RenderScope::ProjectedWorldMarker2D;
    CurrentDirectExactProducer = ProducerToken::RivalMarkerSprani;
    CurrentQueueProjectedMarker = {true, 3.0f, 4.0f, 5.0f};
    {
        ScopedExactProducerSemantic goal(
            RenderScope::ScreenHud, nullptr, true, token);
        if (CurrentScope != RenderScope::ScreenHud ||
            CurrentQueueExactScope != RenderScope::None ||
            NextDrawScope != RenderScope::None ||
            CurrentDirectExactProducer != token ||
            CurrentProjectedMarker() != nullptr ||
            ConsumeForDraw() != RenderScope::ScreenHud)
            return false;
    }
    return CurrentScope == RenderScope::SceneEffect &&
        CurrentQueueExactScope == RenderScope::WorldBillboard &&
        NextDrawScope == RenderScope::ProjectedWorldMarker2D &&
        CurrentDirectExactProducer == ProducerToken::RivalMarkerSprani &&
        CurrentProjectedMarker() != nullptr &&
        CurrentProjectedMarker()->viewX == 3.0f &&
        ConsumeForDraw() == RenderScope::ProjectedWorldMarker2D;
}
static bool CheckStagePrintfBatch()
{
    constexpr auto hud = RenderScope::ScreenHud;
    constexpr auto result = ProducerToken::OutRunStagePrintf;
    constexpr auto progress = ProducerToken::ResultProgress;
    // Direct Sumo_Printf draw: submit under the same source BEFORE its
    // parent E8 returns; never promote an unrelated or mixed buffer.
    return CanFlushD3DXDirectGoalAtExit(
               false, true, true, 2, true, hud, result, hud, result) &&
        !CanFlushD3DXDirectGoalAtExit(
               false, true, true, 2, false, hud, result, hud, result) &&
        !CanFlushD3DXDirectGoalAtExit(
               false, true, true, 2, true, hud, result, hud, progress) &&
        !CanFlushD3DXDirectGoalAtExit(
               true, true, true, 1, true, hud, result, hud, result) &&
        // Queue Begin can occur after the Sumo_Printf SpriteNode select:
        // only its first homogeneous draw may rearm submission.
        CanArmD3DXQueueGoalAfterDraw(
            true, true, true, 1, true, hud, result, hud, result) &&
        !CanArmD3DXQueueGoalAfterDraw(
            true, true, true, 2, true, hud, result, hud, result) &&
        !CanArmD3DXQueueGoalAfterDraw(
            true, true, true, 1, true, hud, result, hud, progress) &&
        !CanArmD3DXQueueGoalAfterDraw(
            false, true, true, 1, true, hud, result, hud, result);
}
static bool CheckQueuedGoalBatch()
{
    constexpr auto hud = RenderScope::ScreenHud;
    for (const auto producer : {
            ProducerToken::ResultProgress,
            ProducerToken::GoalTime020,
            ProducerToken::GoalTime150,
            ProducerToken::OutRunStagePrintf,
            ProducerToken::ResultTextB9200})
    {
        // 1..N sibling D3DX Draws stay in ONE proven owner batch.
        for (unsigned draws = 1; draws < 9; ++draws)
            if (!CanDeferD3DXQueueGoalBatch(
                    true, true, true, true, draws, true,
                    hud, producer, hud, producer))
                return false;
        // Before queue owner is selected, after End/Reset, on a failed
        // Draw or mixed producer, the native fallback must still submit.
        if (CanDeferD3DXQueueGoalBatch(
                false, true, true, true, 2, true,
                hud, producer, hud, producer) ||
            CanDeferD3DXQueueGoalBatch(
                true, false, true, true, 2, true,
                hud, producer, hud, producer) ||
            CanDeferD3DXQueueGoalBatch(
                true, true, false, true, 2, true,
                hud, producer, hud, producer) ||
            CanDeferD3DXQueueGoalBatch(
                true, true, true, false, 2, true,
                hud, producer, hud, producer) ||
            CanDeferD3DXQueueGoalBatch(
                true, true, true, true, 0, true,
                hud, producer, hud, producer) ||
            CanDeferD3DXQueueGoalBatch(
                true, true, true, true, 2, false,
                hud, producer, hud, producer) ||
            CanDeferD3DXQueueGoalBatch(
                true, true, true, true, 2, true,
                hud, producer, hud, ProducerToken::None))
            return false;
    }
    return !CanDeferD3DXQueueGoalBatch(
        true, true, true, true, 2, true,
        hud, ProducerToken::StageExtensionTime,
        hud, ProducerToken::StageExtensionTime) &&
        !CanDeferD3DXQueueGoalBatch(
            true, true, true, true, 2, true,
            RenderScope::WorldBillboard, ProducerToken::GoalTime020,
            RenderScope::WorldBillboard, ProducerToken::GoalTime020);
}

static bool CheckVerifiedB9200GpuOwnership()
{
    using namespace OutRunVR::GameSemantic;
    constexpr auto hud = RenderScope::ScreenHud;
    constexpr auto b9200 = ProducerToken::ResultTextB9200;
    // Only the existing exact original-B9200 stack-return discriminator
    // creates this token. Prove the direct source-exit and queued GPU-batch
    // policies accept it without promoting foreign/mixed/untagged Draws.
    return CanFlushD3DXDirectGoalAtExit(
               false, true, true, 3, true, hud, b9200, hud, b9200) &&
        CanArmD3DXQueueGoalAfterDraw(
               true, true, true, 1, true, hud, b9200, hud, b9200) &&
        CanDeferD3DXQueueGoalBatch(
               true, true, true, true, 3, true, hud, b9200, hud, b9200) &&
        !CanFlushD3DXDirectGoalAtExit(
               false, true, true, 3, false, hud, b9200, hud, b9200) &&
        !CanFlushD3DXDirectGoalAtExit(
               false, true, true, 3, true, hud, b9200,
               hud, ProducerToken::GoalTime020) &&
        !CanFlushD3DXDirectGoalAtExit(
               true, true, true, 3, true, hud, b9200, hud, b9200) &&
        !CanArmD3DXQueueGoalAfterDraw(
               true, true, true, 2, true, hud, b9200, hud, b9200) &&
        !CanDeferD3DXQueueGoalBatch(
               true, true, true, true, 3, false, hud, b9200, hud, b9200) &&
        !CanDeferD3DXQueueGoalBatch(
               true, true, true, true, 3, true, hud, b9200,
               hud, ProducerToken::ResultProgress) &&
        !CanDeferD3DXQueueGoalBatch(
               true, true, true, true, 3, true,
               RenderScope::ScreenOverlay2D, b9200,
               RenderScope::ScreenOverlay2D, b9200) &&
        !CanDrainDirectResultBeforeFirstQueueNode(
               false, true, true, 2, true, hud, b9200,
               RenderScope::None, ProducerToken::None);
}

static bool CheckB9200DirectGpuSource()
{
    using OutRunVR::GoalResult::CanBindDirectB9200D3DXDraw;
    return CanBindDirectB9200D3DXDraw(true, true, false, true, true) &&
        !CanBindDirectB9200D3DXDraw(false, true, false, true, true) &&
        !CanBindDirectB9200D3DXDraw(true, false, false, true, true) &&
        !CanBindDirectB9200D3DXDraw(true, true, true, true, true) &&
        !CanBindDirectB9200D3DXDraw(true, true, false, false, true) &&
        !CanBindDirectB9200D3DXDraw(true, true, false, true, false) &&
        OutRunVR::GoalResult::CheckParentReturnProvenance();
}

int main()
{
    if (!CheckB9200DirectGpuSource()) return 7;
    if (!CheckVerifiedB9200GpuOwnership()) return 6;
    if (!CheckStagePrintfBatch()) return 4;
    if (!CheckQueuedGoalBatch()) return 5;
    if (!CheckDirectGoal(ProducerToken::ResultProgress) ||
        !CheckDirectGoal(ProducerToken::GoalTime020) ||
        !CheckDirectGoal(ProducerToken::GoalTime150) ||
        // Both exact in-game HUD text families can rasterize immediately
        // during gameplay/GOAL without consuming an earlier world token.
        !CheckDirectGoal(ProducerToken::OutRunHudText) ||
        !CheckDirectGoal(ProducerToken::OutRunHudPeripheralText) ||
        // Original result Sumo_Printf parents 0x975EE/0x97727/0x977FB
        // need the same pending-world isolation and exact direct provenance.
        !CheckDirectGoal(ProducerToken::OutRunStagePrintf)) return 1;
    // Nested GOAL producer cannot hijack the current real world queue.
    SpriteQueueDepth = 1;
    CurrentScope = RenderScope::WorldParticle;
    CurrentQueueExactScope = RenderScope::ProjectedWorldMarker2D;
    CurrentDirectExactProducer = ProducerToken::None;
    NextDrawScope = RenderScope::WorldBillboard;
    CurrentQueueProjectedMarker = {true, 9.0f, 8.0f, 7.0f};
    {
        ScopedExactProducerSemantic nested(
            RenderScope::ScreenHud, nullptr, true, ProducerToken::GoalTime150);
        if (CurrentScope != RenderScope::WorldParticle ||
            CurrentQueueExactScope != RenderScope::ProjectedWorldMarker2D ||
            CurrentDirectExactProducer != ProducerToken::None ||
            NextDrawScope != RenderScope::WorldBillboard ||
            CurrentProjectedMarker()->viewX != 9.0f) return 2;
    }
    if (NextDrawScope != RenderScope::WorldBillboard) return 3;
    std::cout << "GOAL progress/time direct and queue semantic smoke PASS\n";
    return 0;
}
