#include "../../src/vr/game/render_semantics.hpp"
#include "../../src/vr/game/goal_result_parent_provenance.hpp"
#include "../../src/vr/game/goal_progress_physical_source.hpp"
#include <iostream>
#include <cmath>
#include "../../src/vr/d3d9/stage_extension_eye_plane.hpp"

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

// Native GOAL eye-source identity is checked only at the real Draw boundary,
// after D3DX direct/queued registration, in both R30 and R33 render paths.
static bool CheckGoalPhysicalBothEyeSources()
{
    using namespace OutRunVR::GoalPhysical;
    const int nodeA = 1, nodeB = 2;
    for (const auto token : {ProducerToken::ResultProgress,
             ProducerToken::GoalTime020, ProducerToken::GoalTime150,
             ProducerToken::OutRunStagePrintf, ProducerToken::ResultTextB9200})
    {
        Source queued{RenderScope::ScreenHud, token, true, &nodeA, 41, 8, 15, 0, 0};
        Source direct{RenderScope::ScreenHud, token, false, nullptr, 0,
            8, 15, 0x1234, 11};
        if (!SameAfterNativeLeft(queued, queued) ||
            !SameAfterNativeLeft(direct, direct)) return false;
        // All five original result families must retain original GPU c64
        // ownership for direct glyph and queued sprite submission.
        auto stampedQueued = queued;
        stampedQueued.rawWvpWriteSerial = 701;
        stampedQueued.rawWvpDrawSerial = 41;
        auto stampedDirect = direct;
        stampedDirect.rawWvpWriteSerial = 702;
        stampedDirect.rawWvpDrawSerial = 42;
        if (!SameAfterNativeLeft(stampedQueued, stampedQueued) ||
            !SameAfterNativeLeft(stampedDirect, stampedDirect)) return false;
        auto changedRaw = stampedQueued;
        ++changedRaw.rawWvpWriteSerial;
        if (SameAfterNativeLeft(stampedQueued, changedRaw)) return false;
        changedRaw = stampedQueued;
        ++changedRaw.rawWvpDrawSerial;
        if (SameAfterNativeLeft(stampedQueued, changedRaw)) return false;
        changedRaw = stampedDirect;
        ++changedRaw.rawWvpWriteSerial;
        if (SameAfterNativeLeft(stampedDirect, changedRaw)) return false;
        changedRaw = stampedDirect;
        ++changedRaw.rawWvpDrawSerial;
        if (SameAfterNativeLeft(stampedDirect, changedRaw)) return false;
        changedRaw = stampedQueued;
        changedRaw.rawWvpDrawSerial = 0;
        if (IsValid(changedRaw) || SameAfterNativeLeft(stampedQueued, changedRaw)) return false;
        changedRaw = stampedDirect;
        changedRaw.rawWvpWriteSerial = 0;
        if (IsValid(changedRaw) || SameAfterNativeLeft(stampedDirect, changedRaw)) return false;
        // Real R30 physical submission must stamp the same original c64
        // generation as R33, even when a nested native LEFT callback writes
        // another matrix for the SAME GOAL producer, node and shader.
        auto r30Before = StampOriginalGameWvpGeneration(queued, true, 901, 77);
        auto r30After = StampOriginalGameWvpGeneration(queued, true, 902, 77);
        if (!SameAfterNativeLeft(r30Before, r30Before) ||
            SameAfterNativeLeft(r30Before, r30After)) return false;
        r30After = StampOriginalGameWvpGeneration(queued, true, 901, 78);
        if (SameAfterNativeLeft(r30Before, r30After)) return false;
        // The original fixed-function fallback accepts absent proof but
        // may not quietly treat an incomplete or newly captured generation
        // as identical to a previously proven one.
        const auto unknown = StampOriginalGameWvpGeneration(queued, false, 901, 77);
        const auto incomplete = StampOriginalGameWvpGeneration(queued, true, 901, 0);
        if (!IsValid(unknown) || !IsValid(incomplete) ||
            unknown.rawWvpWriteSerial != 0 || unknown.rawWvpDrawSerial != 0 ||
            incomplete.rawWvpWriteSerial != 0 || incomplete.rawWvpDrawSerial != 0 ||
            SameAfterNativeLeft(r30Before, unknown) ||
            SameAfterNativeLeft(unknown, r30Before)) return false;
        // No cross-family borrowing: +TIME and world markers are rejected
        // even if their original c64 generation happens to match.
        auto foreignStage = StampOriginalGameWvpGeneration(queued, true, 901, 77);
        foreignStage.producer = ProducerToken::StageExtensionTime;
        auto foreignWorld = StampOriginalGameWvpGeneration(queued, true, 901, 77);
        foreignWorld.scope = RenderScope::WorldBillboard;
        if (SameAfterNativeLeft(r30Before, foreignStage) ||
            SameAfterNativeLeft(r30Before, foreignWorld)) return false;
        // Both absent stamps retain existing native fallback eligibility.
        if (!IsValid(queued) || !IsValid(direct)) return false;
        auto changed = queued;
        changed.node = &nodeB;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; ++changed.queueEpoch;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; changed.producer = ProducerToken::StageExtensionTime;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; changed.scope = RenderScope::ScreenOverlay2D;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; changed.queued = false;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; changed.poseEpoch = 0;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; ++changed.poseEpoch;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = queued; ++changed.drawSerial;
        if (SameAfterNativeLeft(queued, changed)) return false;
        changed = direct; ++changed.shaderEpoch;
        if (SameAfterNativeLeft(direct, changed)) return false;
        changed = direct; changed.shader = 0x2345;
        if (SameAfterNativeLeft(direct, changed)) return false;
        changed = direct; changed.shaderEpoch = 0;
        if (SameAfterNativeLeft(direct, changed)) return false;
        changed = direct; changed.node = &nodeA;
        if (SameAfterNativeLeft(direct, changed)) return false;
        changed = direct; changed.queueEpoch = 1;
        if (SameAfterNativeLeft(direct, changed)) return false;
        changed = direct; changed.queued = true;
        if (SameAfterNativeLeft(direct, changed)) return false;
        changed = direct; changed.producer = ProducerToken::None;
        if (SameAfterNativeLeft(direct, changed)) return false;
    }
    return !IsValid(Source{}) &&
        !IsValid(Source{RenderScope::ScreenHud,
            ProducerToken::StageExtensionTime, false, nullptr, 0, 8, 15, 0, 0}) &&
        !IsValid(Source{RenderScope::ScreenHud,
            ProducerToken::OutRunHudText, false, nullptr, 0, 8, 15, 0, 0}) &&
        !IsValid(Source{RenderScope::WorldBillboard,
            ProducerToken::GoalTime020, false, nullptr, 0, 8, 15, 0, 0});
}


// Verify that the five original GOAL producer families, including both
// progress helpers and final result text, agree with +TIME on the original
// 2D-to-native-eye viewport path. The physical XR RT must not be interpreted
// as the source pixel extent; unknown sprites must retain their old path.
static bool CheckGoalOriginalPresentationPixels()
{
    using namespace OutRunVR::GameSemantic;
    using namespace OutRunVR::GoalPhysical;
    using OutRunVR::StageExtensionPlane::ProjectPixelPairAcrossViewports;
    const float left[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, -0.04f,0,0,1};
    const float right[16]{
        1,0,0,0, 0,1,0,0, 0,0,1,0, 0.04f,0,0,1};
    auto near = [](float a, float b) {
        return std::isfinite(a) && std::fabs(a-b) < 0.02f;
    };
    const ProducerToken goalFamilies[]{
        ProducerToken::ResultProgress, ProducerToken::GoalTime020,
        ProducerToken::GoalTime150, ProducerToken::OutRunStagePrintf,
        ProducerToken::ResultTextB9200};
    for (const auto token : goalFamilies)
    {
        Source draw{RenderScope::ScreenHud, token, false};
        if (!IsGoal(draw) ||
            !CanReprojectFiniteResultHudPlane(draw.scope, draw.producer))
            return false;
        // Original 3440x1440 game source, XR 2496x2688 right/left RT:
        // keep the native 1720x720 screen centre while preserving stereo
        // parallax. Verify both progress and final result families.
        float lx=0, ly=0, rx=0, ry=0;
        if (!ProjectPixelPairAcrossViewports(left,right,1720,720,
                0,0,3440,1440,0,0,2496,2688,1,
                lx,ly,rx,ry) ||
            !near(lx,1198.08f) || !near(rx,1297.92f) ||
            !near(ly,1344.f) || !near(ry,1344.f))
            return false;
        // Native 1:1 game/eye desktop output does not resize results.
        if (!ProjectPixelPairAcrossViewports(left,right,960,540,
                0,0,1920,1080,0,0,1920,1080,1,
                lx,ly,rx,ry) ||
            !near(lx,921.6f) || !near(rx,998.4f) ||
            !near(ly,540.f) || !near(ry,540.f))
            return false;
    }
    for (const auto foreign : {
             ProducerToken::None, ProducerToken::OutRunHudText,
             ProducerToken::StageExtensionTime,
             ProducerToken::DispRankClipSprite})
    {
        if (IsGoal(Source{RenderScope::ScreenHud, foreign}))
            return false;
    }
    if (IsGoal(Source{RenderScope::ScreenOverlay2D,
                     ProducerToken::ResultProgress}) ||
        IsGoal(Source{RenderScope::WorldBillboard,
                     ProducerToken::ResultTextB9200}))
        return false;
    // A bad right eye, invalid native source or missing source extent
    // must publish neither half of the pair.
    const float badEye[16]{};
    float lx=11.f,ly=13.f,rx=17.f,ry=19.f;
    if (ProjectPixelPairAcrossViewports(left,badEye,1720,720,
            0,0,3440,1440,0,0,2496,2688,1,lx,ly,rx,ry) ||
        ProjectPixelPairAcrossViewports(left,right,1720,720,
            0,0,0,1440,0,0,2496,2688,1,lx,ly,rx,ry) ||
        lx!=11.f || ly!=13.f || rx!=17.f || ry!=19.f)
        return false;
    return true;
}

int main()
{
    if (!CheckGoalOriginalPresentationPixels()) return 9;
    if (!CheckGoalPhysicalBothEyeSources()) return 8;
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
