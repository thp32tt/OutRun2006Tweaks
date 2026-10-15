#pragma once

#include "vr/ipc/protocol_v3.hpp"

#include <cstdint>

namespace OutRunVR::IpcV3
{
    // Run identity is distinct from the monotonically increasing frame ID.
    // v2 frame IDs may restart from the same value after the producer restarts.
    struct ShadowFrameStamp
    {
        std::uint32_t clientPid{};
        std::uint32_t runGeneration{};
        std::uint64_t frameId{};
        friend constexpr bool operator==(const ShadowFrameStamp&,
            const ShadowFrameStamp&) = default;
    };

    constexpr bool ShadowFrameNeedsPublish(const ShadowFrameStamp& incoming,
        const ShadowFrameStamp& published) noexcept
    {
        return incoming.clientPid != 0 && incoming.runGeneration != 0 &&
            incoming.frameId != 0 && !(incoming == published);
    }

    // The v2 heartbeat is not the only source of changing client state.
    // Track the complete explicit v3 representation, not just frame/UX fields.
    constexpr bool ShadowClientEqual(const ClientState& a,
        const ClientState& b) noexcept
    {
        return a.clientPid == b.clientPid &&
            a.flags == b.flags &&
            a.presentationMode == b.presentationMode &&
            a.gameState == b.gameState &&
            a.stereoState == b.stereoState &&
            a.lastFailure == b.lastFailure &&
            a.adapterLuidLow == b.adapterLuidLow &&
            a.adapterLuidHigh == b.adapterLuidHigh &&
            a.interopProbeGeneration == b.interopProbeGeneration &&
            a.interopProbeToken == b.interopProbeToken &&
            a.interopProbeHandle == b.interopProbeHandle &&
            a.backbufferWidth == b.backbufferWidth &&
            a.backbufferHeight == b.backbufferHeight &&
            a.lastPresentedFrameId == b.lastPresentedFrameId &&
            a.lastRenderedPoseId == b.lastRenderedPoseId;
    }
}
