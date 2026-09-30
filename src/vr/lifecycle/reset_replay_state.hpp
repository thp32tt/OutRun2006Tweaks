#pragma once

#include <atomic>
#include <cstdint>

namespace OutRunVR::Lifecycle
{
    struct ResetReplayState
    {
        std::atomic<bool> blocked{ false };
        std::uint64_t replayBlocks = 0;
        std::uint64_t lostDeviceBypasses = 0;
    };
}
