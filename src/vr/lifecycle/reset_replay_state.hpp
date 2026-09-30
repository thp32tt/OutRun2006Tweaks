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
        bool firstReplayBlockLogged = false;
        bool firstLostDeviceBypassLogged = false;

        void SetBlocked(bool value) noexcept
        {
            blocked.store(value, std::memory_order_release);
        }

        bool IsBlocked() const noexcept
        {
            return blocked.load(std::memory_order_acquire);
        }
    };
}
