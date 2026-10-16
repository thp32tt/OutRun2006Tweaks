#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <mutex>

namespace OutRunVR::GameSemantic
{
    // Game-level render ownership recovered from the original mod's reverse
    // engineering. This complements D3D-state heuristics; it never replaces
    // the fail-closed target/depth/WVP gates by itself.
    enum class RenderScope : std::uint8_t
    {
        None = 0,
        SceneEffect,
        SkyGlow,
        WorldParticle,
        WorldBillboard,
        // Exact vehicle-relative world anchor that the game already projected
        // into its 640x480 sprite coordinate system before queueing.
        ProjectedWorldMarker2D,
        // Canonical lens/SceneEffect producer at EXE+0xCABE: the game has
        // already projected the light/effect into screen-oriented geometry,
        // but the draw still needs an exact VR owner rather than generic alpha.
        ProjectedScreenEffect2D,
        ReflectionCube,
        // Generic canonical 2D queue content is NOT evidence of game
        // world geometry or an exact named HUD producer. The current
        // R51 R26+HUD renderer nevertheless uses the same finite,
        // recentered HUD-plane eye transform when it can prove a safe
        // original c64 (VS) or source geometry (XYZRHW). Never describe
        // the *current* accepted ScreenOverlay2D GPU route as FOV-only.
        ScreenOverlay2D,
        ScreenHud,
    };

    struct ProjectedMarkerInfo
    {
        bool valid = false;
        float viewX = 0.0f;
        float viewY = 0.0f;
        float viewZ = 0.0f;
    };

    // Bounded diagnostic identity for exact producer families recovered from
    // original-mod callsites. This token never grants render ownership by
    // itself; it only follows already-explicit semantic tags so queue -> c64 ->
    // draw lifetime can be correlated without broadening HUD/world heuristics.
    enum class ProducerToken : std::uint8_t
    {
        None = 0,
        RankMarkerSprani,
        RankMarkerClipSprite,
        ExactScreenHudClipSprite,
        RivalMarkerSprani,
        TextGlyphPutSprite,
        OutRunStagePrintf,
        ResultProgress,
        // Original GOAL stage/result print parent at 19 exact
        // EXE 0x97xxx CALLs -> sub_4B9200; unlike the progress bar
        // calls, these print elapsed record/stage text.
        ResultTextB9200,
        // Three exact 0x989xx sprani producers in original gameplay
        // extension-time transition (NOT 0x97xxx final GOAL result).
        StageExtensionTime,
        GoalTimeHelper,
        OutRunHudText,
        DispRankFirst,
        // Two independent original GOAL E8 helper parents. Keep the
        // generic token for historic records, but distinguish the actual
        // 0xBEA5A vs 0xBEA5F result glyph source in HMD evidence.
        GoalTime020,
        GoalTime150,
        // R64 HMD-confirmed 6th/6 isolate: kind-0 exact DispRank
        // children are not generic result/time/right-aligned clip HUD.
        // Keep their source distinct so D3DXSprite::Flush never widens
        // to menu, result, +TIME, DDS or all ScreenHud.
        DispRankClipSprite,
        // Append-only: retain existing numeric producer tokens in IPC/debug logs.
        OutRunHudPeripheralText,
        LensFlareCentre, // Exact D3A5 -> C993 central sun, never CABE discs.
        CarBaseShadow, // Direct original player-car contact shadow.
        PauseOptionArrow, // Exact SMPAUSEMENU arrows, never generic clips.
    };

    // The GOAL 0-99% progress, its two exact time helpers and the three
    // verified stage-result printf parents have the SAME physical XYZRHW
    // submission risk as +TIME: the source may finish before D3DX Flush.
    // Admit only their exact producer identities to the recentered finite
    // binocular HUD plane. The B9200 glyph family is now admitted ONLY
    // when its original E8 return is proven on the 2C808/2C9DB wrapper
    // stack and propagated onto direct/queued glyph ownership. Unproven
    // deferred D3DX buffers are deliberately NOT added to the GoalOwner
    // batch-flush whitelist (they retain the native End fallback).
    inline constexpr bool CanReprojectFiniteResultHudPlane(
        RenderScope scope, ProducerToken producer) noexcept
    {
        return scope == RenderScope::ScreenHud &&
            (producer == ProducerToken::StageExtensionTime ||
             producer == ProducerToken::GoalTime020 ||
             producer == ProducerToken::GoalTime150 ||
             producer == ProducerToken::ResultProgress ||
             producer == ProducerToken::OutRunStagePrintf ||
             producer == ProducerToken::ResultTextB9200);
    }

    static_assert(CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf));
    static_assert(CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200));
    static_assert(!CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenOverlay2D, ProducerToken::ResultTextB9200));
    static_assert(!CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::DispRankClipSprite));
    static_assert(!CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenOverlay2D, ProducerToken::ResultProgress));
    static_assert(!CanReprojectFiniteResultHudPlane(
        RenderScope::WorldBillboard, ProducerToken::GoalTime020));
    static_assert(!CanReprojectFiniteResultHudPlane(
        RenderScope::ScreenHud, ProducerToken::None));

    // Previous direct D3DX triangles must be submitted under their OLD
    // owner before the first exact +TIME SpriteNode becomes current.
    // This is never permission to relabel an unknown or mixed batch.
    inline constexpr bool CanFlushD3DXPreQueueStageBatch(
        bool wasQueueActive, bool enteringExactStage, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope outgoingScope, ProducerToken outgoingProducer) noexcept
    {
        return homogeneous && (wasQueueActive || enteringExactStage) &&
            pendingScope != RenderScope::None &&
            pendingProducer != ProducerToken::None &&
            pendingScope == outgoingScope &&
            pendingProducer == outgoingProducer;
    }

    // The source E8 can return before its registered D3DX triangles reach
    // the GPU. On the very FIRST SpriteNode, QueueRenderActive is still false
    // and there is no outgoing queue owner to compare. An unrelated incoming
    // node must not implicitly submit that earlier +TIME/GOAL batch under
    // its own producer. Drain only an already tracked homogeneous result
    // batch on the same live ID3DXSprite, before selecting the next node.
    // Do not drain unknown, mixed, reset or B9200-unproved result glyphs.
    inline constexpr bool CanDrainDirectResultBeforeFirstQueueNode(
        bool queueAlreadyActive, bool batchActive, bool exactLiveSprite,
        unsigned pendingDraws, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope incomingScope, ProducerToken incomingProducer) noexcept
    {
        if (queueAlreadyActive || !batchActive || !exactLiveSprite ||
            !homogeneous || pendingDraws == 0u ||
            pendingScope != RenderScope::ScreenHud)
            return false;
        const bool knownResult =
            pendingProducer == ProducerToken::StageExtensionTime ||
            pendingProducer == ProducerToken::GoalTime020 ||
            pendingProducer == ProducerToken::GoalTime150 ||
            pendingProducer == ProducerToken::ResultProgress ||
            pendingProducer == ProducerToken::OutRunStagePrintf ||
            pendingProducer == ProducerToken::PauseOptionArrow;
        return knownResult &&
            (incomingScope != pendingScope ||
             incomingProducer != pendingProducer);
    }
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 3, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime150,
        RenderScope::None, ProducerToken::None));
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::None, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, false, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, false, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 0, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2, false,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200,
        RenderScope::None, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::None,
        RenderScope::None, ProducerToken::None));
    static_assert(!CanDrainDirectResultBeforeFirstQueueNode(
        false, true, true, 2, true,
        RenderScope::WorldBillboard, ProducerToken::StageExtensionTime,
        RenderScope::None, ProducerToken::None));
    static_assert(!CanFlushD3DXPreQueueStageBatch(
        false, true, true, RenderScope::None, ProducerToken::None,
        RenderScope::None, ProducerToken::None));
    static_assert(!CanFlushD3DXPreQueueStageBatch(
        true, false, true, RenderScope::ScreenOverlay2D, ProducerToken::None,
        RenderScope::ScreenOverlay2D, ProducerToken::None));
    static_assert(CanFlushD3DXPreQueueStageBatch(
        true, false, true, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime, RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime));

    // A source-scope exit is the last safe GPU submission boundary for
    // deferred numeric +TIME sprites. Reject prior/foreign/mixed batches:
    // End() must keep its original failure and batching behavior otherwise.
    inline constexpr bool CanFlushD3DXDirectStageAtExit(
        bool queueActive, bool batchActive, bool exactSprite,
        unsigned pendingDraws, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope currentScope, ProducerToken currentProducer) noexcept
    {
        return !queueActive && batchActive && exactSprite &&
            pendingDraws != 0 && homogeneous &&
            pendingScope == RenderScope::ScreenHud &&
            pendingProducer == ProducerToken::StageExtensionTime &&
            currentScope == pendingScope &&
            currentProducer == pendingProducer;
    }

    static_assert(CanFlushD3DXDirectStageAtExit(
        false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanFlushD3DXDirectStageAtExit(
        false, true, true, 2, false,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanFlushD3DXDirectStageAtExit(
        false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanFlushD3DXDirectStageAtExit(
        true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));

    // Begin can run after the stage SpriteNode has been selected. Its
    // initial reset of StageBoundaryReady must not lose the queued Draw's
    // eventual Flush, but only a clean first StageExtensionTime batch may
    // rearm that boundary; mixed/foreign state can never become ScreenHud.
    inline constexpr bool CanArmD3DXQueueStageAfterDraw(
        bool queueActive, bool batchActive, bool exactSprite,
        unsigned pendingDraws, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope currentScope, ProducerToken currentProducer) noexcept
    {
        return queueActive && batchActive && exactSprite &&
            pendingDraws == 1u && homogeneous &&
            pendingScope == RenderScope::ScreenHud &&
            pendingProducer == ProducerToken::StageExtensionTime &&
            currentScope == pendingScope &&
            currentProducer == pendingProducer;
    }

    static_assert(CanArmD3DXQueueStageAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, false, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, true, false, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, true, true, 1, false,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::WorldBillboard, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueStageAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::DispRankFirst));

    // A Begin issued AFTER selecting a GOAL queue node resets the pending
    // queue boundary. Permit only the first successful, homogeneous draw of
    // the exact original GOAL progress or glyph producer to restore it.
    // This is never a generic ScreenHud/StageExtension admission.
    inline constexpr bool CanArmD3DXQueueGoalAfterDraw(
        bool queueActive, bool batchActive, bool exactSprite,
        unsigned pendingDraws, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope currentScope, ProducerToken currentProducer) noexcept
    {
        return queueActive && batchActive && exactSprite &&
            pendingDraws == 1u && homogeneous &&
            pendingScope == RenderScope::ScreenHud &&
            (pendingProducer == ProducerToken::GoalTime020 ||
             pendingProducer == ProducerToken::GoalTime150 ||
             pendingProducer == ProducerToken::ResultProgress ||
             pendingProducer == ProducerToken::OutRunStagePrintf ||
             pendingProducer == ProducerToken::ResultTextB9200 ||
             pendingProducer == ProducerToken::PauseOptionArrow) &&
            currentScope == pendingScope &&
            currentProducer == pendingProducer;
    }

    static_assert(CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime150,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf));
    static_assert(CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, false,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, true, false, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanArmD3DXQueueGoalAfterDraw(true, false, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));

    // Direct GOAL time helpers and the separate 0-99% progress source
    // are distinct from +TIME and queued SpriteNodes. Only submit owned,
    // homogeneous deferred batches while the original caller is alive.
    // while that exact helper remains active, never a foreign/mixed batch.
    // R84 GOAL can issue multiple D3DXSprite Draw calls for one exact
    // queued progress/glyph producer. The original GPU batch must remain
    // under that producer until BeforeQueueNode/BeforeQueueEnd flush it.
    // Deferring a clean batch avoids a driver submission per glyph; an
    // unarmed, direct, mixed, foreign or untracked batch is NEVER deferred.
    inline constexpr bool CanDeferD3DXQueueGoalBatch(
        bool queueActive, bool batchActive, bool exactSprite,
        bool boundaryReady, unsigned pendingDraws, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope currentScope, ProducerToken currentProducer) noexcept
    {
        return queueActive && batchActive && exactSprite &&
            boundaryReady && pendingDraws != 0 && homogeneous &&
            pendingScope == RenderScope::ScreenHud &&
            (pendingProducer == ProducerToken::GoalTime020 ||
             pendingProducer == ProducerToken::GoalTime150 ||
             pendingProducer == ProducerToken::ResultProgress ||
             pendingProducer == ProducerToken::OutRunStagePrintf ||
             pendingProducer == ProducerToken::ResultTextB9200 ||
             pendingProducer == ProducerToken::PauseOptionArrow) &&
            currentScope == pendingScope &&
            currentProducer == pendingProducer;
    }

    static_assert(CanDeferD3DXQueueGoalBatch(true, true, true, true, 3, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(CanDeferD3DXQueueGoalBatch(true, true, true, true, 4, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime150,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf));
    static_assert(CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200));
    static_assert(!CanDeferD3DXQueueGoalBatch(false, true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(!CanDeferD3DXQueueGoalBatch(true, true, true, false, 1, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(!CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, false,
        RenderScope::ScreenHud, ProducerToken::GoalTime150,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(!CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime150,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanDeferD3DXQueueGoalBatch(true, true, true, true, 2, true,
        RenderScope::WorldBillboard, ProducerToken::GoalTime020,
        RenderScope::WorldBillboard, ProducerToken::GoalTime020));

    inline constexpr bool CanFlushD3DXDirectGoalAtExit(
        bool queueActive, bool batchActive, bool exactSprite,
        unsigned pendingDraws, bool homogeneous,
        RenderScope pendingScope, ProducerToken pendingProducer,
        RenderScope currentScope, ProducerToken currentProducer) noexcept
    {
        return !queueActive && batchActive && exactSprite &&
            pendingDraws != 0 && homogeneous &&
            pendingScope == RenderScope::ScreenHud &&
            (pendingProducer == ProducerToken::GoalTime020 ||
             pendingProducer == ProducerToken::GoalTime150 ||
             pendingProducer == ProducerToken::ResultProgress ||
             pendingProducer == ProducerToken::OutRunStagePrintf ||
             pendingProducer == ProducerToken::ResultTextB9200 ||
             pendingProducer == ProducerToken::PauseOptionArrow) &&
            currentScope == pendingScope &&
            currentProducer == pendingProducer;
    }

    static_assert(CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(CanFlushD3DXDirectGoalAtExit(false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime150,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf));
    static_assert(CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultTextB9200,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 2, false,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::OutRunStagePrintf,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 2, false,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::ResultProgress));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 2, true,
        RenderScope::ScreenHud, ProducerToken::ResultProgress,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime150));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
        RenderScope::ScreenHud, ProducerToken::StageExtensionTime));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, true, 1, false,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanFlushD3DXDirectGoalAtExit(true, true, true, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));
    static_assert(!CanFlushD3DXDirectGoalAtExit(false, true, false, 1, true,
        RenderScope::ScreenHud, ProducerToken::GoalTime020,
        RenderScope::ScreenHud, ProducerToken::GoalTime020));

    inline thread_local RenderScope CurrentScope = RenderScope::None;
    // An explicit SpriteNode producer owns its render space through the
    // complete queue draw. Temporary helper scopes must not replace it.
    // Generic untagged ScreenOverlay2D is deliberately excluded.
    inline thread_local RenderScope CurrentQueueExactScope = RenderScope::None;
    // The native queue is read by ConsumeForDraw before its deferred scope
    // selection; declare the thread-local owner before that inline function.
    inline thread_local unsigned SpriteQueueDepth = 0;
    inline thread_local RenderScope NextDrawScope = RenderScope::None;
    inline thread_local unsigned ExternalOverlaySemanticDepth = 0;
    // Exact C993 draw can nest ordinary SceneEffect helper scopes. Preserve
    // its producer through the actual GPU draw, not merely the parent E8.
    // Queue execution and external F11 overlays retain higher precedence.
    inline thread_local unsigned ExactLensCentreGpuDrawDepth = 0;

    inline constexpr bool DirectLensCentreOwnsGpuDraw(
        bool exactCentreActive, bool queueActive, bool externalOverlay) noexcept
    {
        return exactCentreActive && !queueActive && !externalOverlay;
    }
    static_assert(DirectLensCentreOwnsGpuDraw(true, false, false));
    static_assert(!DirectLensCentreOwnsGpuDraw(true, true, false));
    static_assert(!DirectLensCentreOwnsGpuDraw(true, false, true));
    static_assert(!DirectLensCentreOwnsGpuDraw(false, false, false));

    inline bool ExactLensCentreDrawOwnsSemantic() noexcept;

    inline const char* Name(RenderScope scope) noexcept
    {
        switch (scope)
        {
        case RenderScope::SceneEffect: return "SCENE_EFFECT";
        case RenderScope::SkyGlow: return "SKY_GLOW";
        case RenderScope::WorldParticle: return "WORLD_PARTICLE";
        case RenderScope::WorldBillboard: return "WORLD_BILLBOARD";
        case RenderScope::ProjectedWorldMarker2D: return "PROJECTED_WORLD_MARKER_2D";
        case RenderScope::ProjectedScreenEffect2D: return "PROJECTED_SCREEN_EFFECT_2D";
        case RenderScope::ReflectionCube: return "REFLECTION_CUBE";
        case RenderScope::ScreenOverlay2D: return "SCREEN_OVERLAY_2D";
        case RenderScope::ScreenHud: return "SCREEN_HUD";
        default: return "NONE";
        }
    }

    inline const char* Name(ProducerToken token) noexcept
    {
        switch (token)
        {
        case ProducerToken::RankMarkerSprani: return "RANK_MARKER_SPRANI";
        case ProducerToken::RankMarkerClipSprite: return "RANK_MARKER_CLIP";
        case ProducerToken::ExactScreenHudClipSprite: return "EXACT_SCREEN_HUD_CLIP";
        case ProducerToken::RivalMarkerSprani: return "RIVAL_MARKER_SPRANI";
        case ProducerToken::TextGlyphPutSprite: return "TEXT_GLYPH_PUTSPRITE";
        case ProducerToken::OutRunStagePrintf: return "OUTRUN_STAGE_PRINT";
        case ProducerToken::ResultProgress: return "OUTRUN_RESULT_PROGRESS";
        case ProducerToken::ResultTextB9200: return "OUTRUN_RESULT_TEXT_B9200";
        case ProducerToken::StageExtensionTime: return "OUTRUN_STAGE_EXTENSION_TIME";
        case ProducerToken::GoalTimeHelper: return "GOAL_TIME_HELPER";
        case ProducerToken::OutRunHudText: return "OUTRUN_HUD_TEXT";
        case ProducerToken::OutRunHudPeripheralText: return "OUTRUN_HUD_PERIPHERAL_TEXT";
        case ProducerToken::DispRankFirst: return "DISPLAY_RANK_FIRST";
        case ProducerToken::GoalTime020: return "GOAL_TIME_HELPER_020";
        case ProducerToken::GoalTime150: return "GOAL_TIME_HELPER_150";
        case ProducerToken::DispRankClipSprite: return "DISPRANK_KIND0_CLIP";
        case ProducerToken::LensFlareCentre: return "LENS_FLARE_CENTRE_C993";
        case ProducerToken::CarBaseShadow: return "CAR_BASE_SHADOW_WORLD";
        case ProducerToken::PauseOptionArrow: return "PAUSE_OPTION_ARROW";
        default: return "NONE";
        }
    }

    class ScopedRenderSemantic
    {
        RenderScope previous_ = RenderScope::None;
    public:
        explicit ScopedRenderSemantic(RenderScope scope) noexcept
            : previous_(CurrentScope)
        {
            CurrentScope = scope;
        }
        ~ScopedRenderSemantic()
        {
            CurrentScope = previous_;
        }
        ScopedRenderSemantic(const ScopedRenderSemantic&) = delete;
        ScopedRenderSemantic& operator=(const ScopedRenderSemantic&) = delete;
    };

    class ScopedExternalOverlaySemantic
    {
        RenderScope previous_ = RenderScope::None;
    public:
        explicit ScopedExternalOverlaySemantic(RenderScope scope) noexcept
            : previous_(CurrentScope)
        {
            ++ExternalOverlaySemanticDepth;
            CurrentScope = scope;
        }
        ~ScopedExternalOverlaySemantic()
        {
            if (ExternalOverlaySemanticDepth != 0)
                --ExternalOverlaySemanticDepth;
            CurrentScope = previous_;
        }
        ScopedExternalOverlaySemantic(const ScopedExternalOverlaySemantic&) = delete;
        ScopedExternalOverlaySemantic& operator=(const ScopedExternalOverlaySemantic&) = delete;
    };

    inline RenderScope EffectiveScope() noexcept
    {
        // F11 is an external overlay, never a game SpriteNode consumer.
        if (ExternalOverlaySemanticDepth != 0)
            return CurrentScope;
        if (ExactLensCentreDrawOwnsSemantic())
            return RenderScope::WorldBillboard;
        if (CurrentQueueExactScope == RenderScope::ScreenHud ||
            CurrentQueueExactScope == RenderScope::WorldBillboard ||
            CurrentQueueExactScope == RenderScope::ProjectedWorldMarker2D)
            return CurrentQueueExactScope;
        return CurrentScope;
    }

    inline void ArmNextDraw(RenderScope scope) noexcept
    {
        NextDrawScope = scope;
    }

    inline RenderScope ConsumeForDraw() noexcept
    {
        // External UI such as the F11 ImGui overlay is not a game producer.
        // Never let it consume a pending game semantic token.
        if (ExternalOverlaySemanticDepth != 0)
            return CurrentScope;
        // A nested SceneEffect/one-shot helper must not steal the exact C993
        // centre's physical Draw. ScopedExactProducerSemantic restores its
        // pending token after this original draw completes.
        if (ExactLensCentreDrawOwnsSemantic())
            return RenderScope::WorldBillboard;
        // R84 physical DrawPrimitive consumes one-shot scopes here, before
        // R33/R30 classify the selected original SpriteNode. An earlier
        // TIME RECORD/screen-text one-shot must not be consumed by a distinct
        // producer-owned +TIME, GOAL, pause, rank or world queue node. The
        // exact tag already identifies the entire node's native GPU route;
        // preserve the pending token for its own later, non-queued draw.
        // Untagged queue nodes retain the original one-shot fallback.
        if (SpriteQueueDepth != 0 &&
            (CurrentQueueExactScope == RenderScope::ScreenHud ||
             CurrentQueueExactScope == RenderScope::WorldBillboard ||
             CurrentQueueExactScope == RenderScope::ProjectedWorldMarker2D))
            return CurrentQueueExactScope;
        if (NextDrawScope != RenderScope::None)
        {
            const RenderScope scope = NextDrawScope;
            NextDrawScope = RenderScope::None;
            return scope;
        }
        return EffectiveScope();
    }

    inline bool ForceZeroDisparity(RenderScope scope) noexcept
    {
        return scope == RenderScope::SkyGlow ||
            scope == RenderScope::ScreenOverlay2D;
    }

    inline bool CorroboratesWorld(RenderScope scope) noexcept
    {
        return scope == RenderScope::WorldParticle ||
            scope == RenderScope::WorldBillboard;
    }

    inline bool CorroboratesProjectedWorldMarker(RenderScope scope) noexcept
    {
        return scope == RenderScope::ProjectedWorldMarker2D;
    }

    inline bool CorroboratesProjectedScreenEffect(RenderScope scope) noexcept
    {
        return scope == RenderScope::ProjectedScreenEffect2D;
    }

    inline bool CorroboratesScreenOverlay2D(RenderScope scope) noexcept
    {
        return scope == RenderScope::ScreenOverlay2D;
    }

    // R26 HMD-proven queue-owned generic HUD uses the recentered finite
    // screen plane, not head-following per-eye FOV-only affine. Neither an
    // unqueued world overlay nor F11's external UI may acquire this owner.
    constexpr bool QueueOverlayNeedsFiniteHudPlane(
        RenderScope scope, bool queued, bool external) noexcept
    {
        return scope == RenderScope::ScreenOverlay2D && queued && !external;
    }
    static_assert(QueueOverlayNeedsFiniteHudPlane(
        RenderScope::ScreenOverlay2D, true, false));
    static_assert(!QueueOverlayNeedsFiniteHudPlane(
        RenderScope::ScreenOverlay2D, false, false));
    static_assert(!QueueOverlayNeedsFiniteHudPlane(
        RenderScope::ScreenOverlay2D, true, true));
    static_assert(!QueueOverlayNeedsFiniteHudPlane(
        RenderScope::WorldParticle, true, false));
    static_assert(!QueueOverlayNeedsFiniteHudPlane(
        RenderScope::ScreenHud, true, false));

    inline bool CorroboratesHud(RenderScope scope) noexcept
    {
        // ScreenOverlay2D is intentionally NOT a finite/world-locked HUD.
        // Only exact producer evidence may enter ScreenHud.
        return scope == RenderScope::ScreenHud;
    }

    // The stereo SkyGlow source must be captured before a real screen/UI
    // producer, NOT before an exact world-space sun, marker, or scene effect.
    // The outer draw hooks and the successful per-eye path must agree on this
    // boundary; otherwise the lens centre can prematurely freeze both bloom
    // source eyes and exclude later genuine world lighting from the snapshot.
    constexpr bool IsSkyGlowPreHudBoundary(RenderScope scope) noexcept
    {
        return scope == RenderScope::ScreenHud ||
            scope == RenderScope::ScreenOverlay2D;
    }
    static_assert(IsSkyGlowPreHudBoundary(RenderScope::ScreenHud));
    static_assert(IsSkyGlowPreHudBoundary(RenderScope::ScreenOverlay2D));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::WorldBillboard));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::SceneEffect));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::ProjectedWorldMarker2D));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::ProjectedScreenEffect2D));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::SkyGlow));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::WorldParticle));
    static_assert(!IsSkyGlowPreHudBoundary(RenderScope::None));

    // Canonical OR2006C2C.EXE queue renderer recovered by static reverse analysis:
    //   0x42D734 enters the per-priority SpriteNode walk,
    //   0x42D762 begins one node, and
    //   0x42DCB4 is the common epilogue.
    // The queue provides a stable per-node execution boundary, but queue
    // membership alone is NOT semantic finite-HUD evidence. Untagged nodes are
    // generic ScreenOverlay2D: correct only the OpenXR asymmetric-FOV mapping,
    // without head inverse, eye translation, depth reset, or world-plane
    // placement. Exact producer evidence may still tag ScreenHud/WorldBillboard.
    struct SpriteNodeSemanticTag
    {
        const void* node = nullptr;
        RenderScope scope = RenderScope::None;
        ProducerToken producer = ProducerToken::None;
        std::uint64_t serial = 0;
        ProjectedMarkerInfo projectedMarker{};
    };

    inline constexpr std::size_t SpriteNodeSemanticCapacity = 0x230;

    // Exact semantic producers and the canonical SpriteNode queue renderer are
    // not guaranteed to execute on the same thread. Keep only the tag registry
    // shared and synchronized; render cursor/scope state below remains local.
    // PublishedCount lets the overwhelmingly common no-tag path avoid taking
    // the mutex at all.
    inline std::array<SpriteNodeSemanticTag,
        SpriteNodeSemanticCapacity> SpriteNodeSemanticTags{};
    inline std::size_t SpriteNodeSemanticCount = 0;
    inline std::atomic<std::size_t> SpriteNodeSemanticPublishedCount{ 0 };
    inline std::mutex SpriteNodeSemanticMutex;
    // Definite-miss filter for dense SpriteNode queues. Positive hints still
    // take the original locked exact-pointer path; hash bits never grant HUD,
    // world or per-eye ownership. Writers update bit counts under the mutex.
    inline constexpr unsigned SpriteNodeSemanticHintBits = 256;
    inline std::array<std::atomic<std::uint64_t>, 4>
        SpriteNodeSemanticHintWords{};
    inline std::array<std::uint16_t, SpriteNodeSemanticHintBits>
        SpriteNodeSemanticHintRefCounts{};

    struct SpriteNodeHintPair { unsigned first; unsigned second; };

    inline SpriteNodeHintPair SpriteNodeSemanticHintFor(
        const void* node) noexcept
    {
        std::uint64_t key = static_cast<std::uint64_t>(
            reinterpret_cast<std::uintptr_t>(node)) >> 3;
        key ^= key >> 32;
        std::uint32_t h = static_cast<std::uint32_t>(key);
        h ^= h >> 16;
        h *= 0x7feb352du;
        h ^= h >> 15;
        h *= 0x846ca68bu;
        h ^= h >> 16;
        return { h & 255u, (h >> 8) & 255u };
    }

    inline bool SpriteNodeSemanticMaybeHasTag(const void* node) noexcept
    {
        const auto bits = SpriteNodeSemanticHintFor(node);
        const auto has = [](unsigned bit) noexcept {
            return (SpriteNodeSemanticHintWords[bit >> 6].load(
                std::memory_order_acquire) & (1ull << (bit & 63u))) != 0;
        };
        return has(bits.first) && has(bits.second);
    }

    inline void SpriteNodeSemanticRememberHint(const void* node) noexcept
    {
        const auto bits = SpriteNodeSemanticHintFor(node);
        const auto add = [](unsigned bit) noexcept {
            if (SpriteNodeSemanticHintRefCounts[bit]++ == 0)
                SpriteNodeSemanticHintWords[bit >> 6].fetch_or(
                    1ull << (bit & 63u), std::memory_order_release);
        };
        add(bits.first);
        if (bits.second != bits.first)
            add(bits.second);
    }

    inline void SpriteNodeSemanticForgetHint(const void* node) noexcept
    {
        const auto bits = SpriteNodeSemanticHintFor(node);
        const auto remove = [](unsigned bit) noexcept {
            auto& count = SpriteNodeSemanticHintRefCounts[bit];
            if (count != 0 && --count == 0)
                SpriteNodeSemanticHintWords[bit >> 6].fetch_and(
                    ~(1ull << (bit & 63u)), std::memory_order_release);
        };
        remove(bits.first);
        if (bits.second != bits.first)
            remove(bits.second);
    }

    inline std::atomic<std::uint64_t> SpriteNodeSemanticNextSerial{ 1 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticRegistered{ 0 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticConsumed{ 0 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticStaleCleared{ 0 };
    inline thread_local std::uint64_t SpriteQueueSemanticCutoff = 0;

    inline thread_local RenderScope SpriteQueuePreviousScope = RenderScope::None;
    // Monotonic per-thread identity for the canonical queue node currently
    // being rendered. This is diagnostic/provenance state only; it does not
    // change semantic classification or draw ownership.
    inline thread_local const void* CurrentSpriteQueueNode = nullptr;
    inline thread_local std::uint64_t SpriteQueueNodeEpoch = 0;
    inline thread_local ProducerToken CurrentSpriteQueueProducer =
        ProducerToken::None;
    // Direct original-game glyph rasterization occurs before SpriteNodes
    // exist. Its token must never overwrite the active queue cursor.
    inline thread_local ProducerToken CurrentDirectExactProducer =
        ProducerToken::None;
    // Source-call identity: raw c64 from a previous identical shader is not
    // owned by this original central sun. Each D3A5 invocation gets an epoch.
    inline thread_local std::uint64_t CurrentLensCentreCallEpoch = 0;
    inline thread_local std::uint64_t NextLensCentreCallEpoch = 0;
    inline thread_local ProjectedMarkerInfo CurrentQueueProjectedMarker{};

    inline const void* CurrentQueueNode() noexcept
    {
        return CurrentSpriteQueueNode;
    }

    inline std::uint64_t CurrentQueueNodeEpoch() noexcept
    {
        return SpriteQueueNodeEpoch;
    }

    inline ProducerToken CurrentQueueProducerToken() noexcept
    {
        return CurrentSpriteQueueProducer;
    }

    inline bool ExactLensCentreDrawOwnsSemantic() noexcept
    {
        return DirectLensCentreOwnsGpuDraw(
            ExactLensCentreGpuDrawDepth != 0, SpriteQueueDepth != 0,
            ExternalOverlaySemanticDepth != 0);
    }

    inline ProducerToken CurrentRenderProducerToken() noexcept
    {
        // Queue nodes and external UI never inherit the central sun's
        // provenance. Within this one C993 draw, a nested SceneEffect or
        // temporary direct helper cannot rebrand the source c64 upload.
        if (SpriteQueueDepth != 0)
            return CurrentSpriteQueueProducer;
        if (ExactLensCentreDrawOwnsSemantic())
            return ProducerToken::LensFlareCentre;
        return CurrentDirectExactProducer;
    }

    class ScopedExactLensCentreGpuDraw final
    {
        bool active_ = false;
    public:
        explicit ScopedExactLensCentreGpuDraw(bool exactCentre) noexcept
            : active_(exactCentre && SpriteQueueDepth == 0 &&
                ExternalOverlaySemanticDepth == 0)
        {
            if (active_)
                ++ExactLensCentreGpuDrawDepth;
        }
        ~ScopedExactLensCentreGpuDraw()
        {
            if (active_)
                --ExactLensCentreGpuDrawDepth;
        }
        ScopedExactLensCentreGpuDraw(const ScopedExactLensCentreGpuDraw&) = delete;
        ScopedExactLensCentreGpuDraw& operator=(const ScopedExactLensCentreGpuDraw&) = delete;
    };

    inline const ProjectedMarkerInfo* CurrentProjectedMarker() noexcept
    {
        return CurrentQueueProjectedMarker.valid
            ? &CurrentQueueProjectedMarker : nullptr;
    }

    inline bool QueueRenderActive() noexcept
    {
        return SpriteQueueDepth != 0;
    }

    // Immutable source-side identity for ONE physical GPU primitive.
    // The R33 raster dispatcher samples the current original-game scope,
    // producer and queue epoch once. No ownership is inferred from alpha,
    // texture, FVF, or primitive size. A deferred D3DX batch can enter this
    // scope only through ScopedExactProducerSemantic at its real Flush/End.
    struct PhysicalDrawCommand final
    {
        RenderScope scope = RenderScope::None;
        ProducerToken producer = ProducerToken::None;
        const void* queueNode = nullptr;
        std::uint64_t queueEpoch = 0;
        bool queued = false;
        // Exact D3A5 parent invocation captured at the same physical GPU
        // primitive boundary as scope/producer.  Never consult mutable TLS
        // later and accidentally correlate C993 with another sun invocation.
        std::uint64_t lensCentreCallEpoch = 0;

        constexpr bool IsDirectWorldLensCentre() const noexcept
        {
            return !queued && scope == RenderScope::WorldBillboard &&
                producer == ProducerToken::LensFlareCentre &&
                lensCentreCallEpoch != 0;
        }

        // Quest's native flare callback is distinct from the HUD/2D flush.
        // Our original C993 source can only enter the dedicated game-WVP
        // world route. In particular, a temporary null VS / POSITIONT state
        // must not bypass C993 provenance through R30's generic XYZRHW path.
        // A missing exact world WVP remains ONE unchanged game draw at R33.
        constexpr bool CanUseGenericXyzrhwStereo() const noexcept
        {
            // This is an original world-space player contact shadow, not an
            // already-projected generic 2D sprite. Never collapse its car
            // transform onto R30's finite HUD plane before source WVP proof.
            return !IsDirectWorldLensCentre() &&
                !IsDirectCarBaseShadow();
        }

        constexpr bool IsDirectCarBaseShadow() const noexcept
        {
            return !queued && scope == RenderScope::WorldParticle &&
                producer == ProducerToken::CarBaseShadow;
        }

        constexpr bool IsSourceProvenHud() const noexcept
        {
            return scope == RenderScope::ScreenHud &&
                producer != ProducerToken::None;
        }

        // R84 physical dispatch must never route *source-identified screen*
        // commands into R29's verified road/vehicle WVP when R30 could not
        // establish binocular HUD/marker ownership. Direct exact HUD and
        // queued projected rank glyphs keep their ONE native original draw.
        // Generic overlays, untagged sprites and actual world draws still
        // use the original R29 decision; a token by itself grants nothing.
        constexpr bool NeedsScreenStereoOrOriginal() const noexcept
        {
            return IsSourceProvenHud() ||
                (queued && producer != ProducerToken::None &&
                 scope == RenderScope::ProjectedWorldMarker2D);
        }

        // A failed/unknown R30 screen pass is not permission for R31/R29 to
        // borrow the previous road/vehicle WVP. Exact HUD, generic original
        // SpriteNode overlay, projected markers, SkyGlow and screen-space
        // flare effects may use their own proven R30 stereo path, otherwise
        // preserve ONE original draw. This veto is independent of alpha/Z
        // state and does not inhibit opaque world, car shadows or particles.
        constexpr bool DeniesGenericWorldFallback() const noexcept
        {
            return scope == RenderScope::ScreenHud ||
                scope == RenderScope::ScreenOverlay2D ||
                scope == RenderScope::ProjectedWorldMarker2D ||
                scope == RenderScope::ProjectedScreenEffect2D ||
                scope == RenderScope::SkyGlow;
        }

        // +TIME and the exact original GOAL producer family own a finite
        // HUD-plane GPU draw, not the last verified perspective road c64.
        // Only the R30/R33 physically proven HUD stereo route may replace
        // their original draw. A missing HUD proof must never fall into
        // R31's cached fast-world WVP, even if shader/pose happen to match.
        constexpr bool IsExactFiniteResultHud() const noexcept
        {
            return CanReprojectFiniteResultHudPlane(scope, producer);
        }
    };

    // An ambiguous screen draw can NEVER inherit R31's cached road WVP.
    static_assert(PhysicalDrawCommand{RenderScope::ScreenHud,
        ProducerToken::None, nullptr, 0, false, 0}
        .DeniesGenericWorldFallback());
    static_assert(PhysicalDrawCommand{RenderScope::ScreenOverlay2D,
        ProducerToken::None, nullptr, 0, true, 1}
        .DeniesGenericWorldFallback());
    static_assert(PhysicalDrawCommand{RenderScope::ProjectedWorldMarker2D,
        ProducerToken::None, nullptr, 0, true, 1}
        .DeniesGenericWorldFallback());
    static_assert(PhysicalDrawCommand{RenderScope::ProjectedScreenEffect2D,
        ProducerToken::None, nullptr, 0, false, 0}
        .DeniesGenericWorldFallback());
    static_assert(PhysicalDrawCommand{RenderScope::SkyGlow,
        ProducerToken::None, nullptr, 0, false, 0}
        .DeniesGenericWorldFallback());
    static_assert(!PhysicalDrawCommand{RenderScope::WorldParticle,
        ProducerToken::None, nullptr, 0, false, 0}
        .DeniesGenericWorldFallback());
    static_assert(!PhysicalDrawCommand{RenderScope::WorldBillboard,
        ProducerToken::None, nullptr, 0, false, 0}
        .DeniesGenericWorldFallback());
    static_assert(!PhysicalDrawCommand{RenderScope::SceneEffect,
        ProducerToken::None, nullptr, 0, false, 0}
        .DeniesGenericWorldFallback());

    static_assert(!PhysicalDrawCommand{RenderScope::WorldParticle,
        ProducerToken::CarBaseShadow, nullptr, 0, false, 0}
        .CanUseGenericXyzrhwStereo(),
        "direct player shadow must keep original world-space geometry");
    static_assert(PhysicalDrawCommand{RenderScope::ScreenOverlay2D,
        ProducerToken::None, nullptr, 0, false, 0}
        .CanUseGenericXyzrhwStereo(),
        "ordinary original screen sprites remain eligible");

    inline PhysicalDrawCommand CapturePhysicalDrawCommand() noexcept
    {
        const bool isQueued = QueueRenderActive();
        const ProducerToken producer = CurrentRenderProducerToken();
        const bool exactLensCentre = !isQueued &&
            producer == ProducerToken::LensFlareCentre &&
            ExactLensCentreDrawOwnsSemantic();
        return { EffectiveScope(), producer,
            isQueued ? CurrentQueueNode() : nullptr,
            isQueued ? CurrentQueueNodeEpoch() : 0,
            isQueued,
            exactLensCentre ? CurrentLensCentreCallEpoch : 0 };
    }

    // A direct original-game source CALL may rasterize before it appends any
    // SpriteNode. ScopedRenderSemantic alone changes CurrentScope, but the
    // previously selected queue node still wins EffectiveScope() and its old
    // projected anchor still wins CurrentProjectedMarker(). Rebind BOTH only
    // for a non-queue direct producer, then restore them unconditionally.
    // Already selected SpriteNodes remain the authority during queue draws.
    class ScopedExactProducerSemantic final
    {
        RenderScope savedScope_ = RenderScope::None;
        RenderScope savedQueueScope_ = RenderScope::None;
        RenderScope savedPendingDraw_ = RenderScope::None;
        ProjectedMarkerInfo savedProjectedMarker_{};
        ProducerToken savedDirectProducer_ = ProducerToken::None;
        bool active_ = false;
        bool isolatePendingDraw_ = false;

    public:
        explicit ScopedExactProducerSemantic(
            RenderScope scope,
            const ProjectedMarkerInfo* marker = nullptr,
            bool isolatePendingDraw = false,
            ProducerToken directProducer = ProducerToken::None) noexcept
            : active_(SpriteQueueDepth == 0 && scope != RenderScope::None),
              isolatePendingDraw_(active_ && isolatePendingDraw)
        {
            if (!active_)
                return;
            savedScope_ = CurrentScope;
            savedQueueScope_ = CurrentQueueExactScope;
            savedProjectedMarker_ = CurrentQueueProjectedMarker;
            savedDirectProducer_ = CurrentDirectExactProducer;
            // Only the opted-in direct draw shields and restores a previously
            // armed producer token. All other exact producers are unchanged.
            if (isolatePendingDraw_)
            {
                savedPendingDraw_ = NextDrawScope;
                NextDrawScope = RenderScope::None;
            }
            CurrentQueueExactScope = RenderScope::None;
            CurrentDirectExactProducer = directProducer;
            CurrentQueueProjectedMarker =
                scope == RenderScope::ProjectedWorldMarker2D &&
                marker && marker->valid ? *marker : ProjectedMarkerInfo{};
            CurrentScope = scope;
        }

        ~ScopedExactProducerSemantic()
        {
            if (!active_)
                return;
            CurrentScope = savedScope_;
            CurrentQueueExactScope = savedQueueScope_;
            CurrentDirectExactProducer = savedDirectProducer_;
            CurrentQueueProjectedMarker = savedProjectedMarker_;
            if (isolatePendingDraw_)
                NextDrawScope = savedPendingDraw_;
        }

        ScopedExactProducerSemantic(
            const ScopedExactProducerSemantic&) = delete;
        ScopedExactProducerSemantic& operator=(
            const ScopedExactProducerSemantic&) = delete;
    };

    inline void RegisterSpriteNodeScope(
        const void* node, RenderScope scope,
        ProducerToken producer = ProducerToken::None,
        const ProjectedMarkerInfo* projectedMarker = nullptr) noexcept
    {
        if (!node || scope == RenderScope::None)
            return;

        // Publish serial and tag atomically with respect to queue cutoff.
        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        const std::uint64_t serial =
            SpriteNodeSemanticNextSerial.fetch_add(
                1, std::memory_order_acq_rel);
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node == node)
            {
                SpriteNodeSemanticTags[i].scope = scope;
                SpriteNodeSemanticTags[i].producer = producer;
                SpriteNodeSemanticTags[i].serial = serial;
                SpriteNodeSemanticTags[i].projectedMarker =
                    projectedMarker ? *projectedMarker : ProjectedMarkerInfo{};
                SpriteNodeSemanticPublishedCount.store(
                    SpriteNodeSemanticCount, std::memory_order_release);
                SpriteNodeSemanticRegistered.fetch_add(
                    1, std::memory_order_relaxed);
                return;
            }
        }

        if (SpriteNodeSemanticCount < SpriteNodeSemanticTags.size())
        {
            SpriteNodeSemanticTags[SpriteNodeSemanticCount++] =
                { node, scope, producer, serial,
                  projectedMarker ? *projectedMarker : ProjectedMarkerInfo{} };
            SpriteNodeSemanticRememberHint(node);
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteNodeSemanticRegistered.fetch_add(
                1, std::memory_order_relaxed);
            return;
        }

        // Exact producers are sparse. If a broken frame fills the bounded
        // table, replace the oldest tag rather than silently losing semantic
        // ownership for the remainder of the run.
        std::size_t oldest = 0;
        for (std::size_t i = 1; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].serial <
                SpriteNodeSemanticTags[oldest].serial)
                oldest = i;
        }
        SpriteNodeSemanticForgetHint(SpriteNodeSemanticTags[oldest].node);
        SpriteNodeSemanticTags[oldest] =
            { node, scope, producer, serial,
              projectedMarker ? *projectedMarker : ProjectedMarkerInfo{} };
        SpriteNodeSemanticRememberHint(node);
        SpriteNodeSemanticRegistered.fetch_add(
            1, std::memory_order_relaxed);
        SpriteNodeSemanticStaleCleared.fetch_add(
            1, std::memory_order_relaxed);
    }

    inline RenderScope PeekSpriteNodeScope(
        const void* node,
        RenderScope fallback = RenderScope::None,
        ProducerToken* producer = nullptr,
        ProjectedMarkerInfo* projectedMarker = nullptr) noexcept
    {
        if (producer)
            *producer = ProducerToken::None;
        if (projectedMarker)
            *projectedMarker = {};
        if (!node ||
            SpriteNodeSemanticPublishedCount.load(
                std::memory_order_acquire) == 0 ||
            !SpriteNodeSemanticMaybeHasTag(node))
            return fallback;

        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node != node)
                continue;
            // A producer can publish the next frame while the renderer is
            // draining this SpriteNode walk. A newer tag is NOT evidence for
            // the old queue node, even if its allocator reuses the pointer.
            // Keep that tag intact for the next queue walk's cutoff.
            if (SpriteQueueDepth != 0 &&
                SpriteNodeSemanticTags[i].serial > SpriteQueueSemanticCutoff)
                return fallback;
            if (producer)
                *producer = SpriteNodeSemanticTags[i].producer;
            if (projectedMarker)
                *projectedMarker = SpriteNodeSemanticTags[i].projectedMarker;
            return SpriteNodeSemanticTags[i].scope;
        }
        return fallback;
    }

    inline ProducerToken PeekSpriteNodeProducerToken(
        const void* node) noexcept
    {
        ProducerToken producer = ProducerToken::None;
        (void)PeekSpriteNodeScope(
            node, RenderScope::None, &producer);
        return producer;
    }

    inline RenderScope ConsumeSpriteNodeScope(
        const void* node,
        RenderScope fallback = RenderScope::ScreenOverlay2D,
        ProducerToken* producer = nullptr,
        bool* exactTag = nullptr) noexcept
    {
        if (producer)
            *producer = ProducerToken::None;
        if (exactTag)
            *exactTag = false;
        if (!node ||
            SpriteNodeSemanticPublishedCount.load(
                std::memory_order_acquire) == 0 ||
            !SpriteNodeSemanticMaybeHasTag(node))
            return fallback;

        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        CurrentQueueProjectedMarker = {};
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node != node)
                continue;
            // Peek and physical queue consumption MUST agree on the same
            // frame cutoff. Never consume a next-frame +TIME/HUD/world tag
            // on today's GPU draw or erase its hash hint prematurely.
            if (SpriteQueueDepth != 0 &&
                SpriteNodeSemanticTags[i].serial > SpriteQueueSemanticCutoff)
                return fallback;
            const RenderScope scope = SpriteNodeSemanticTags[i].scope;
            if (exactTag)
                *exactTag = true;
            if (producer)
                *producer = SpriteNodeSemanticTags[i].producer;
            CurrentQueueProjectedMarker =
                SpriteNodeSemanticTags[i].projectedMarker;
            SpriteNodeSemanticForgetHint(node);
            SpriteNodeSemanticTags[i] =
                SpriteNodeSemanticTags[--SpriteNodeSemanticCount];
            SpriteNodeSemanticTags[SpriteNodeSemanticCount] = {};
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteNodeSemanticConsumed.fetch_add(
                1, std::memory_order_relaxed);
            return scope;
        }
        return fallback;
    }

    inline void BeginSpriteQueueRender() noexcept
    {
        if (SpriteQueueDepth++ == 0)
        {
            CurrentQueueExactScope = RenderScope::None;
            SpriteQueuePreviousScope = CurrentScope;
            // Serial publication and queue snapshot must share a mutex.
            {
                std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
                const std::uint64_t next =
                    SpriteNodeSemanticNextSerial.load(std::memory_order_acquire);
                SpriteQueueSemanticCutoff = next > 0 ? next - 1 : 0;
            }
            // Runtime ea7c322d proved queue->SCREEN_HUD is too strong, while
            // runtime 9554272a proved queue->NONE leaves 2D content duplicated
            // at identical D3D screen coordinates, which does not converge under
            // asymmetric OpenXR eye FOV. Generic queue content therefore owns
            // only the per-eye FOV affine, not the finite world-locked HUD plane.
            CurrentScope = RenderScope::ScreenOverlay2D;
        }
    }

    inline void SelectSpriteQueueNode(const void* node) noexcept
    {
        // Do not hook the canonical queue entry at RVA 0x2D734. Two real
        // crashes (EXE+0x2D738 and EXE+0x2D73E) proved that relocating the
        // tiny entry/prologue block with a mid-hook is not runtime-safe.
        //
        // The first node at RVA 0x2D762 is the earliest point where semantic
        // ownership is actually needed, so lazily open the queue scope here.
        if (!SpriteQueueDepth)
        {
            SpriteQueueDepth = 1;
            SpriteQueuePreviousScope = CurrentScope;
            // Serial publication and queue snapshot must share a mutex.
            {
                std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
                const std::uint64_t next =
                    SpriteNodeSemanticNextSerial.load(std::memory_order_acquire);
                SpriteQueueSemanticCutoff = next > 0 ? next - 1 : 0;
            }
        }
        CurrentSpriteQueueNode = node;
        CurrentQueueProjectedMarker = {};
        CurrentQueueExactScope = RenderScope::None;
        if (++SpriteQueueNodeEpoch == 0)
            ++SpriteQueueNodeEpoch;
        CurrentSpriteQueueProducer = ProducerToken::None;
        bool exactTag = false;
        CurrentScope = ConsumeSpriteNodeScope(
            node, RenderScope::ScreenOverlay2D,
            &CurrentSpriteQueueProducer, &exactTag);
        if (exactTag && (CurrentScope == RenderScope::ScreenHud ||
                         CurrentScope == RenderScope::WorldBillboard ||
                         CurrentScope == RenderScope::ProjectedWorldMarker2D))
            CurrentQueueExactScope = CurrentScope;
    }

    inline void EndSpriteQueueRender() noexcept
    {
        if (!SpriteQueueDepth)
            return;
        if (--SpriteQueueDepth == 0)
        {
            CurrentScope = SpriteQueuePreviousScope;
            SpriteQueuePreviousScope = RenderScope::None;
            CurrentSpriteQueueNode = nullptr;
            CurrentSpriteQueueProducer = ProducerToken::None;
            CurrentQueueProjectedMarker = {};
            CurrentQueueExactScope = RenderScope::None;

            // Remove only tags that existed when this queue walk began. A
            // producer thread may already be preparing the next frame while
            // the renderer is finishing this one; preserve those newer tags.
            std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
            std::size_t write = 0;
            for (std::size_t read = 0;
                read < SpriteNodeSemanticCount; ++read)
            {
                const auto& tag = SpriteNodeSemanticTags[read];
                if (tag.serial != 0 &&
                    tag.serial <= SpriteQueueSemanticCutoff)
                {
                    SpriteNodeSemanticForgetHint(tag.node);
                    SpriteNodeSemanticStaleCleared.fetch_add(
                        1, std::memory_order_relaxed);
                    continue;
                }
                if (write != read)
                    SpriteNodeSemanticTags[write] = tag;
                ++write;
            }
            while (SpriteNodeSemanticCount > write)
                SpriteNodeSemanticTags[--SpriteNodeSemanticCount] = {};
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteQueueSemanticCutoff = 0;
        }
    }

}
