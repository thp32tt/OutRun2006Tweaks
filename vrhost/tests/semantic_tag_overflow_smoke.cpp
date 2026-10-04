#include "vr/game/render_semantics.hpp"

#include <cstdint>
#include <mutex>

namespace
{
using namespace OutRunVR::GameSemantic;

const void* Node(std::size_t index) noexcept
{
    return reinterpret_cast<const void*>(
        static_cast<std::uintptr_t>(0x10000u + index * 0x10u));
}

void ResetState()
{
    std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
    for (auto& tag : SpriteNodeSemanticTags)
        tag = {};
    SpriteNodeSemanticCount = 0;
    SpriteNodeSemanticPublishedCount.store(0, std::memory_order_release);
    SpriteNodeSemanticNextSerial.store(1, std::memory_order_release);
    SpriteNodeSemanticRegistered.store(0, std::memory_order_release);
    SpriteNodeSemanticConsumed.store(0, std::memory_order_release);
    SpriteNodeSemanticStaleCleared.store(0, std::memory_order_release);
    SpriteNodeSemanticOverflowRejected.store(0, std::memory_order_release);
    CurrentQueueProjectedMarker = {};
    CurrentQueueOwner = SpriteNodeOwner::None;
}
}

int main()
{
    using namespace OutRunVR::GameSemantic;
    ResetState();

    for (std::size_t i = 0; i < SpriteNodeSemanticCapacity; ++i)
        RegisterSpriteNodeScope(Node(i), RenderScope::ScreenHud);

    if (SpriteNodeSemanticCount != SpriteNodeSemanticCapacity) return 1;
    if (SpriteNodeSemanticPublishedCount.load(std::memory_order_acquire) !=
        SpriteNodeSemanticCapacity) return 2;
    if (SpriteNodeSemanticOverflowRejected.load(std::memory_order_acquire) != 0)
        return 3;

    // Updating an already-published node remains valid even while full.
    RegisterSpriteNodeScope(Node(1), RenderScope::WorldBillboard);
    if (SpriteNodeSemanticCount != SpriteNodeSemanticCapacity) return 4;
    if (SpriteNodeSemanticOverflowRejected.load(std::memory_order_acquire) != 0)
        return 5;

    const void* overflowNode = Node(SpriteNodeSemanticCapacity + 1);
    RegisterSpriteNodeScope(
        overflowNode, RenderScope::ProjectedWorldMarker2D);

    if (SpriteNodeSemanticCount != SpriteNodeSemanticCapacity) return 6;
    if (SpriteNodeSemanticPublishedCount.load(std::memory_order_acquire) !=
        SpriteNodeSemanticCapacity) return 7;
    if (SpriteNodeSemanticOverflowRejected.load(std::memory_order_acquire) != 1)
        return 8;
    if (SpriteNodeSemanticStaleCleared.load(std::memory_order_acquire) != 0)
        return 9;

    // The oldest live tag must survive overflow; F16 specifically forbids
    // replacing it to make room for the newest producer.
    if (ConsumeSpriteNodeScope(Node(0)) != RenderScope::ScreenHud) return 10;
    if (ConsumeSpriteNodeScope(Node(1)) != RenderScope::WorldBillboard) return 11;

    // The rejected newest node must fall back rather than stealing another
    // queued node's exact owner.
    if (ConsumeSpriteNodeScope(overflowNode) != RenderScope::ScreenOverlay2D)
        return 12;

    // Once capacity is available the same producer can be accepted normally.
    RegisterSpriteNodeScope(
        overflowNode, RenderScope::ProjectedWorldMarker2D);
    if (SpriteNodeSemanticOverflowRejected.load(std::memory_order_acquire) != 1)
        return 13;
    if (ConsumeSpriteNodeScope(overflowNode) !=
        RenderScope::ProjectedWorldMarker2D) return 14;

    return 0;
}
