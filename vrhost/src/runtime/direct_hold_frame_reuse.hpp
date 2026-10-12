#pragma once

#include <cstdint>

// A repeated XR candidate can retry its projection after the DirectGPU pair
// has already been copied into host-owned hold textures. The producer ring is
// not ACKed until the queued sampling completes. Only reuse the hold for the
// exact same immutable producer frame and the same opened D3D11 resources.
// This deliberately does not compare frame ID alone: slots, generations and
// numerical handles may be reused after Reset or a game restart.
namespace OutRunVrDirectHoldReuse
{
    struct FrameKey
    {
        std::uint32_t frameId = 0;
        std::uint32_t slot = 0;
        std::uint32_t generation = 0;
        std::uint32_t runGeneration = 0;
        std::uint32_t gamePid = 0;
        std::uint32_t leftHandle = 0;
        std::uint32_t rightHandle = 0;
        std::uintptr_t leftResource = 0;
        std::uintptr_t rightResource = 0;
    };

    constexpr bool CanReuse(bool holdValid, const FrameKey& held,
        const FrameKey& incoming) noexcept
    {
        return holdValid && incoming.frameId != 0 &&
            incoming.generation != 0 && incoming.runGeneration != 0 &&
            incoming.gamePid != 0 && incoming.leftHandle != 0 &&
            incoming.rightHandle != 0 && incoming.leftResource != 0 &&
            incoming.rightResource != 0 &&
            held.frameId == incoming.frameId &&
            held.slot == incoming.slot &&
            held.generation == incoming.generation &&
            held.runGeneration == incoming.runGeneration &&
            held.gamePid == incoming.gamePid &&
            held.leftHandle == incoming.leftHandle &&
            held.rightHandle == incoming.rightHandle &&
            held.leftResource == incoming.leftResource &&
            held.rightResource == incoming.rightResource;
    }
}
