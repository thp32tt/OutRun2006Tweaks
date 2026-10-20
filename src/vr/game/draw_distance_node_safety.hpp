#pragma once
#include <cstddef>
#include <cstdint>

// Host-independent policy used by the original game draw-distance hook.
// The DrawObject_Internal list has a terminal 0xFFFF entry in addition to
// its 4096 real entries; the seen bitmap covers every non-sentinel uint16 ID.
namespace OutRunVR::DrawDistanceSafety
{
    inline constexpr std::size_t SeenNodeCount = 1u << 16;
    inline constexpr std::size_t DrawListCapacity = 4096;
    inline constexpr std::size_t DrawListStorage = DrawListCapacity + 1;

    constexpr bool IsKnownExclusionIndex(std::uint16_t id, std::size_t count) noexcept
    {
        return static_cast<std::size_t>(id) < count;
    }

    // A rejected behind-section node must remain eligible in its real
    // section; only actually admitted nodes participate in deduplication.
    constexpr bool ShouldQueueNode(bool alreadySeen, bool excluded,
        int csOffset, bool increaseEnabled) noexcept
    {
        return !alreadySeen && ((csOffset == 0 && increaseEnabled) || !excluded);
    }

    constexpr bool CanAppend(std::size_t count) noexcept
    {
        return count < DrawListCapacity;
    }
}
