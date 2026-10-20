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
        // Exact projected rank/rival parents already own the recovered
        // Calc3D2D vehicle anchor. Native put_sprite_ex/put_sprite_ex2 must
        // not discard this stronger source proof in favor of a broad caller
        // RVA WorldBillboard classification.
        GameSemantic::ProjectedMarkerInfo projectedMarker{};
    };

    inline Snapshot Capture() noexcept
    {
        const auto* marker = GameSemantic::CurrentProjectedMarker();
        return { GameSemantic::CurrentScope,
                 GameSemantic::CurrentDirectExactProducer,
                 GameSemantic::QueueRenderActive(),
                 GameSemantic::ExternalOverlaySemanticDepth != 0,
                 GameSemantic::SpriteNodeSemanticNextSerial.load(
                     std::memory_order_acquire),
                 marker ? *marker : GameSemantic::ProjectedMarkerInfo{} };
    }

    constexpr bool SameProjectedMarker(
        const GameSemantic::ProjectedMarkerInfo& a,
        const GameSemantic::ProjectedMarkerInfo& b) noexcept
    {
        return a.valid && b.valid &&
            a.viewX == b.viewX &&
            a.viewY == b.viewY &&
            a.viewZ == b.viewZ;
    }

    constexpr ProducerToken ProvenProjectedVehicleMarkerProducer(
        Snapshot before, Snapshot after) noexcept
    {
        if (before.scope != RenderScope::ProjectedWorldMarker2D ||
            after.scope != RenderScope::ProjectedWorldMarker2D ||
            before.producer != after.producer ||
            before.queueActive || after.queueActive ||
            before.externalOverlay || after.externalOverlay ||
            !SameProjectedMarker(
                before.projectedMarker, after.projectedMarker))
            return ProducerToken::None;

        switch (before.producer)
        {
        case ProducerToken::RankMarkerSprani:
        case ProducerToken::RankMarkerClipSprite:
        case ProducerToken::RivalMarkerSprani:
            return before.producer;
        default:
            return ProducerToken::None;
        }
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
        // BA9D0 can synchronously enqueue a native SpriteNode while its
        // original text E8 parent is still on the stack. The parent scope
        // has already been admitted on a verified original CALL; carry its
        // exact HUD family across node registration and Sumo replay.
        case ProducerToken::OutRunHudText:
        case ProducerToken::OutRunHudPeripheralText:
            return before.producer;
        default:
            return ProducerToken::None;
        }
    }


    // The shared original BA9D0 text helper has an unclassified inner
    // put_sprite caller: only a verified outer original E8 HUD text scope
    // may supply the missing ScreenHud owner to its newly queued nodes.
    // Other exact sources (GOAL, +TIME, rank) retain their own paths.
    constexpr bool CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken token) noexcept
    {
        return token == ProducerToken::OutRunHudText ||
               token == ProducerToken::OutRunHudPeripheralText;
    }
    static_assert(CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::OutRunHudText));
    static_assert(CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::OutRunHudPeripheralText));
    static_assert(!CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::None));
    static_assert(!CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::StageExtensionTime));
    static_assert(!CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::ResultTextB9200));
    static_assert(!CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::RankMarkerSprani));
    static_assert(!CanCarryExactHudTextAtUnknownCallsite(
        ProducerToken::LensFlareCentre));

    // Mode and render-queue entry conditions must survive the *entire*
    // native put_sprite_ex/put_sprite_ex2 call. Merely checking VR at
    // return wrongly promotes desktop nodes after an off->on toggle.
    // Preserve the independent live-root/tail and nested-node proofs.
    constexpr bool CanAdmitNativeDirectNodeTags(
        bool vrAtEntry, bool vrAtReturn, Snapshot entry,
        Snapshot onReturn) noexcept
    {
        return vrAtEntry && vrAtReturn &&
            !entry.queueActive && !onReturn.queueActive &&
            !entry.externalOverlay && !onReturn.externalOverlay &&
            entry.scope == onReturn.scope &&
            entry.producer == onReturn.producer;
    }

    constexpr bool TestNativeDirectVrAdmission() noexcept
    {
        const Snapshot hud{RenderScope::ScreenHud,
            ProducerToken::DispRankFirst, false, false, 42};
        const Snapshot generic{RenderScope::None,
            ProducerToken::None, false, false, 7};
        if (!CanAdmitNativeDirectNodeTags(true, true, hud, hud) ||
            !CanAdmitNativeDirectNodeTags(true, true, generic, generic) ||
            CanAdmitNativeDirectNodeTags(false, true, hud, hud) ||
            CanAdmitNativeDirectNodeTags(true, false, hud, hud) ||
            CanAdmitNativeDirectNodeTags(false, false, hud, hud))
            return false;
        auto queued = hud;
        queued.queueActive = true;
        if (CanAdmitNativeDirectNodeTags(true, true, queued, hud) ||
            CanAdmitNativeDirectNodeTags(true, true, hud, queued))
            return false;
        auto overlay = hud;
        overlay.externalOverlay = true;
        if (CanAdmitNativeDirectNodeTags(true, true, overlay, hud) ||
            CanAdmitNativeDirectNodeTags(true, true, hud, overlay))
            return false;
        auto changed = hud;
        changed.producer = ProducerToken::ResultTextB9200;
        if (CanAdmitNativeDirectNodeTags(true, true, hud, changed))
            return false;
        changed = hud;
        changed.scope = RenderScope::WorldBillboard;
        if (CanAdmitNativeDirectNodeTags(true, true, hud, changed))
            return false;
        changed = hud;
        changed.registrationSerial++;
        return CanAdmitNativeDirectNodeTags(true, true, hud, changed);
    }
    static_assert(TestNativeDirectVrAdmission(),
        "Direct native HUD sprites must reject mode/queue/producer changes");


    constexpr Snapshot ProjectedMarkerSource(
        ProducerToken token, float z = -64.0f) noexcept
    {
        return { RenderScope::ProjectedWorldMarker2D, token,
                 false, false, 77,
                 { true, 1.0f, 2.0f, z } };
    }
    static_assert(ProvenProjectedVehicleMarkerProducer(
        ProjectedMarkerSource(ProducerToken::RankMarkerSprani),
        ProjectedMarkerSource(ProducerToken::RankMarkerSprani)) ==
        ProducerToken::RankMarkerSprani);
    static_assert(ProvenProjectedVehicleMarkerProducer(
        ProjectedMarkerSource(ProducerToken::RankMarkerClipSprite),
        ProjectedMarkerSource(ProducerToken::RankMarkerClipSprite)) ==
        ProducerToken::RankMarkerClipSprite);
    static_assert(ProvenProjectedVehicleMarkerProducer(
        ProjectedMarkerSource(ProducerToken::RivalMarkerSprani),
        ProjectedMarkerSource(ProducerToken::RivalMarkerSprani)) ==
        ProducerToken::RivalMarkerSprani);
    static_assert(ProvenProjectedVehicleMarkerProducer(
        ProjectedMarkerSource(ProducerToken::RankMarkerSprani),
        ProjectedMarkerSource(ProducerToken::RankMarkerSprani, -32.0f)) ==
        ProducerToken::None);
    static_assert(ProvenProjectedVehicleMarkerProducer(
        ProjectedMarkerSource(ProducerToken::RankMarkerSprani),
        ProjectedMarkerSource(ProducerToken::RivalMarkerSprani)) ==
        ProducerToken::None);

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
        RenderScope::ScreenHud, Hud(ProducerToken::OutRunHudText),
        Hud(ProducerToken::OutRunHudText)) == ProducerToken::OutRunHudText);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::OutRunHudPeripheralText),
        Hud(ProducerToken::OutRunHudPeripheralText)) == ProducerToken::OutRunHudPeripheralText);
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::OutRunHudText),
        Hud(ProducerToken::OutRunHudPeripheralText)) == ProducerToken::None);
    static_assert(!CanAdmitNativeDirectNodeTags(
        true, true, Hud(ProducerToken::OutRunHudText),
        Hud(ProducerToken::OutRunHudPeripheralText)));
    static_assert(ProvenScreenHudProducer(
        RenderScope::ScreenHud, Hud(ProducerToken::OutRunHudText),
        {RenderScope::ScreenHud, ProducerToken::OutRunHudText, false, true})
        == ProducerToken::None);
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
