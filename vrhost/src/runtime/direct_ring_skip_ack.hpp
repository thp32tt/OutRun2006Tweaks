#pragma once
#include <cstdint>

// Only a frame provably older than the selected DirectGPU frame may be
// acknowledged without GPU consumption. Matching the transport generation
// alone is insufficient after a game restart or a recycled producer slot.
namespace OutRunVrDirectRingSkipAck
{
    struct FrameIdentity
    {
        std::uint32_t frameId{};
        std::uint32_t generation{};
        std::uint32_t runGeneration{};
        std::uint32_t gamePid{};
    };

    template <class FrameBefore>
    constexpr bool CanAcknowledge(const FrameIdentity& candidate,
        const FrameIdentity& selected, std::uint32_t lastDisplayed,
        FrameBefore before) noexcept
    {
        return candidate.frameId != 0 && selected.frameId != 0 &&
            candidate.generation != 0 &&
            candidate.generation == selected.generation &&
            candidate.runGeneration != 0 &&
            candidate.runGeneration == selected.runGeneration &&
            candidate.gamePid != 0 && candidate.gamePid == selected.gamePid &&
            before(candidate.frameId, selected.frameId) &&
            (lastDisplayed == 0 || before(lastDisplayed, candidate.frameId));
    }

    // Compiled by the real R23 Windows host as well as the portable fixture.
    constexpr auto StrictBefore = [](std::uint32_t lhs,
        std::uint32_t rhs) noexcept { return lhs < rhs; };
    static_assert(CanAcknowledge({9, 3, 7, 100}, {12, 3, 7, 100}, 8, StrictBefore));
    static_assert(!CanAcknowledge({13, 3, 7, 100}, {12, 3, 7, 100}, 8, StrictBefore));
    static_assert(!CanAcknowledge({9, 3, 6, 100}, {12, 3, 7, 100}, 8, StrictBefore));
    static_assert(!CanAcknowledge({9, 3, 7, 101}, {12, 3, 7, 100}, 8, StrictBefore));
    static_assert(!CanAcknowledge({9, 2, 7, 100}, {12, 3, 7, 100}, 8, StrictBefore));
    static_assert(!CanAcknowledge({9, 3, 7, 100}, {12, 3, 7, 100}, 9, StrictBefore));
}
