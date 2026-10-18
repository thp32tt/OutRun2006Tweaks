#pragma once

#include "render_semantics.hpp"

// A direct native SpriteNode may be emitted while an exact original parent
// owns the HUD source. Queue reachability proves *which nodes* were appended;
// this independent before/after proof prevents a nested sprite callback from
// borrowing another producer's exact token (or an external ImGui/queue token).
// Unknown callers retain their current scope-only, native fallback behavior.
namespace OutRunVR::DirectSpriteSource
{
    using GameSemantic::ProducerToken;
    using GameSemantic::RenderScope;

    struct Snapshot final
    {
        RenderScope scope = RenderScope::None;
        ProducerToken producer = ProducerToken::None;
        bool queueActive = false;
        bool externalOverlay = false;
    };

    inline Snapshot Capture() noexcept
    {
        return { GameSemantic::CurrentScope,
                 GameSemantic::CurrentDirectExactProducer,
                 GameSemantic::QueueRenderActive(),
                 GameSemantic::ExternalOverlaySemanticDepth != 0 };
    }

    constexpr ProducerToken ProvenScreenHudProducer(
        RenderScope classified, Snapshot before,
        Snapshot after) noexcept
    {
        if (classified != RenderScope::ScreenHud ||
            before.scope != classified || after.scope != classified ||
            before.producer != after.producer ||
            before.queueActive || after.queueActive ||
            before.externalOverlay || after.externalOverlay)
            return ProducerToken::None;

        // Only existing original-EXE source-backed HUD parent scopes may
        // provide a producer. Do NOT promote broad return-RVA classification,
        // all result glyphs, rank WORLD markers, or generic screen overlays.
        switch (before.producer)
        {
        case ProducerToken::DispRankFirst:
        case ProducerToken::DispRankClipSprite:
        case ProducerToken::StageExtensionTime:
        case ProducerToken::ResultProgress:
        case ProducerToken::ResultTextB9200:
        case ProducerToken::GoalTime020:
        case ProducerToken::GoalTime150:
        case ProducerToken::OutRunStagePrintf:
            return before.producer;
        default:
            return ProducerToken::None;
        }
    }

    constexpr Snapshot Hud(ProducerToken token) noexcept
    {
        return { RenderScope::ScreenHud, token, false, false };
    }
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::DispRankFirst),
        Hud(ProducerToken::DispRankFirst)) == ProducerToken::DispRankFirst);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::DispRankClipSprite),
        Hud(ProducerToken::DispRankClipSprite)) == ProducerToken::DispRankClipSprite);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::StageExtensionTime),
        Hud(ProducerToken::StageExtensionTime)) == ProducerToken::StageExtensionTime);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::ResultTextB9200),
        Hud(ProducerToken::ResultTextB9200)) == ProducerToken::ResultTextB9200);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::None),
        Hud(ProducerToken::None)) == ProducerToken::None);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::StageExtensionTime),
        Hud(ProducerToken::ResultProgress)) == ProducerToken::None);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::StageExtensionTime),
        {RenderScope::ScreenHud, ProducerToken::StageExtensionTime, true, false})
        == ProducerToken::None);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::StageExtensionTime),
        {RenderScope::ScreenHud, ProducerToken::StageExtensionTime, false, true})
        == ProducerToken::None);
    static_assert(ProvenScreenHudProducer(
        RenderScope::WorldBillboard, Hud(ProducerToken::StageExtensionTime),
        Hud(ProducerToken::StageExtensionTime)) == ProducerToken::None);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::CarBaseShadow),
        Hud(ProducerToken::CarBaseShadow)) == ProducerToken::None);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::ResultProgress),
        {RenderScope::SceneEffect, ProducerToken::ResultProgress, false, false})
        == ProducerToken::None);
}
