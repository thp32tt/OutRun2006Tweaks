#pragma once
#include "../game/render_semantics.hpp"
#include <cstdint>

// Admission for exact R84 shader ScreenHud original-game c64. Pose,
// shader epoch and draw-age checks remain with the renderer; this additional
// proof binds the write to the exact HUD producer and active SpriteNode.
// A previously head/eye-modified live c64 or unrelated producer is never
// promoted when the game did not publish a matching original matrix.
namespace OutRunVR::HudOriginalWvp
{
    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;
    struct Provenance
    {
        RenderScope currentScope, writtenScope;
        ProducerToken currentProducer, writtenProducer;
        bool queueActive;
        const void* currentNode;
        const void* writtenNode;
        std::uint64_t currentNodeEpoch, writtenNodeEpoch;
    };

    constexpr bool OwnsProducer(const Provenance& e) noexcept
    {
        if (e.currentScope != RenderScope::ScreenHud ||
            e.writtenScope != RenderScope::ScreenHud ||
            e.currentProducer == ProducerToken::None ||
            e.currentProducer != e.writtenProducer)
            return false;
        if (!e.queueActive)
        {
            // A direct original-game HUD upload must not inherit a selected
            // SpriteNode from a just-finished/reentrant queue submission.
            // Queue epochs are historical and may remain nonzero after
            // leaving the queue, but the live node must be absent on BOTH
            // sides of the direct c64 -> physical draw transaction.
            return e.currentNode == nullptr && e.writtenNode == nullptr;
        }
        return e.currentNode != nullptr &&
            e.currentNode == e.writtenNode &&
            e.currentNodeEpoch != 0 &&
            e.currentNodeEpoch == e.writtenNodeEpoch;
    }

    // R26_SAFE's source-queue ScreenOverlay2D drew on the same finite HUD
    // plane as exact rank/6th text; R84 retained only tagged ScreenHud.
    // Re-admit an untagged overlay *only* with a live same-node/epoch c64
    // original, not a coincidentally matching shader or stale world matrix.
    // A missing original source keeps the one-draw R33 native fallback.
    constexpr bool OwnsGenericQueuedOverlay(const Provenance& e) noexcept
    {
        return e.currentScope == RenderScope::ScreenOverlay2D &&
            e.writtenScope == RenderScope::ScreenOverlay2D &&
            e.currentProducer == ProducerToken::None &&
            e.writtenProducer == ProducerToken::None &&
            e.queueActive &&
            e.currentNode != nullptr &&
            e.currentNode == e.writtenNode &&
            e.currentNodeEpoch != 0 &&
            e.currentNodeEpoch == e.writtenNodeEpoch;
    }

    constexpr Provenance DirectHud{
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudPeripheralText,
        ProducerToken::OutRunHudPeripheralText,
        false, nullptr, nullptr, 0, 0
    };
    // Real producer/queue transaction regressions compiled in the R84
    // game and host: a stale selected node must never turn a direct HUD
    // upload into a source-proven stereo eye. A nonzero historical epoch
    // alone is not a live node and must not suppress valid direct text.
    inline constexpr unsigned char QueuedNodeOne = 1;
    inline constexpr unsigned char QueuedNodeTwo = 2;
    static_assert(OwnsProducer(DirectHud));
    static_assert(OwnsProducer({
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudPeripheralText,
        ProducerToken::OutRunHudPeripheralText,
        false, nullptr, nullptr, 11, 9
    }));
    static_assert(!OwnsProducer({
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudPeripheralText,
        ProducerToken::OutRunHudPeripheralText,
        false, &QueuedNodeOne, nullptr, 11, 9
    }));
    static_assert(!OwnsProducer({
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudPeripheralText,
        ProducerToken::OutRunHudPeripheralText,
        false, nullptr, &QueuedNodeOne, 11, 9
    }));
    static_assert(OwnsProducer({
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudText, ProducerToken::OutRunHudText,
        true, &QueuedNodeOne, &QueuedNodeOne, 12, 12
    }));
    static_assert(!OwnsProducer({
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudText, ProducerToken::OutRunHudText,
        true, &QueuedNodeTwo, &QueuedNodeOne, 13, 12
    }));
    static_assert(!OwnsProducer({
        RenderScope::ScreenHud, RenderScope::ScreenHud,
        ProducerToken::OutRunHudText, ProducerToken::OutRunHudText,
        true, &QueuedNodeOne, &QueuedNodeOne, 13, 12
    }));
    static_assert(!OwnsProducer({
        RenderScope::ScreenHud, RenderScope::WorldBillboard,
        DirectHud.currentProducer, DirectHud.writtenProducer,
        false, nullptr, nullptr, 0, 0
    }));
    static_assert(!OwnsProducer({
        DirectHud.currentScope, DirectHud.writtenScope,
        DirectHud.currentProducer, ProducerToken::StageExtensionTime,
        false, nullptr, nullptr, 0, 0
    }));
    static_assert(!OwnsProducer({
        DirectHud.currentScope, DirectHud.writtenScope,
        ProducerToken::None, ProducerToken::None,
        false, nullptr, nullptr, 0, 0
    }));
}
