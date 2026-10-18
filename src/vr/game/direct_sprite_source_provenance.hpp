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
        // Preserve the exact native source-entry registration generation.
        std::uint64_t registrationSerial = 0;
    };

    inline Snapshot Capture() noexcept
    {
        return { GameSemantic::CurrentScope,
                 GameSemantic::CurrentDirectExactProducer,
                 GameSemantic::QueueRenderActive(),
                 GameSemantic::ExternalOverlaySemanticDepth != 0,
                 GameSemantic::SpriteNodeSemanticNextSerial.load(
                     std::memory_order_acquire) };
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

    // The native sprite call can reenter another exact source. Keep those
    // newly registered children, but allow unknown, same, and old tags to
    // inherit the proven enclosing source through the existing queue path.
    constexpr bool TestNestedDirectSpriteOwner() noexcept
    {
        const Snapshot entry{
            RenderScope::ScreenHud, ProducerToken::StageExtensionTime,
            false, false, 42 };
        return GameSemantic::PreserveNestedExactSpriteOwner(
                   ProducerToken::GoalTime020,
                   entry.producer, 43, entry.registrationSerial) &&
               GameSemantic::PreserveNestedExactSpriteOwner(
                   ProducerToken::RankMarkerSprani,
                   ProducerToken::None, 44, entry.registrationSerial) &&
               !GameSemantic::PreserveNestedExactSpriteOwner(
                   ProducerToken::None,
                   entry.producer, 45, entry.registrationSerial) &&
               !GameSemantic::PreserveNestedExactSpriteOwner(
                   entry.producer,
                   entry.producer, 46, entry.registrationSerial) &&
               !GameSemantic::PreserveNestedExactSpriteOwner(
                   ProducerToken::GoalTime020,
                   entry.producer, 41, entry.registrationSerial) &&
               !GameSemantic::PreserveNestedExactSpriteOwner(
                   ProducerToken::GoalTime020,
                   entry.producer, 43, 0);
    }
    static_assert(TestNestedDirectSpriteOwner(),
        "Native direct SpriteNodes must preserve exact nested producers");

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
