#pragma once

#include <atomic>
#include <cstdint>

namespace OutRunVR::RuntimeEligibility
{
    // Keep host freshness identical to the validated pose reader. All game-side
    // VR decisions (WVP injection, stereo replay and bootstrap) consume this
    // single frame-boundary decision instead of maintaining independent clocks.
    inline constexpr std::int64_t HostStaleMs = 250;

    inline std::atomic<bool> HostFresh{ false };
    inline std::atomic<bool> StereoAllowed{ false };
    inline std::atomic<bool> RecoveryPending{ true };

    inline void FailClosed() noexcept
    {
        HostFresh.store(false, std::memory_order_release);
        StereoAllowed.store(false, std::memory_order_release);
        RecoveryPending.store(true, std::memory_order_release);
    }

    inline void ObserveFreshHost() noexcept
    {
        HostFresh.store(true, std::memory_order_release);
        // Do not reopen stereo here. A fresh host after a stall still needs a
        // newly verified zero-disparity color/depth baseline before injection.
    }

    inline void BaselineVerified() noexcept
    {
        if (!HostFresh.load(std::memory_order_acquire))
            return;
        RecoveryPending.store(false, std::memory_order_release);
        StereoAllowed.store(true, std::memory_order_release);
    }

    inline bool MayInjectStereo() noexcept
    {
        return HostFresh.load(std::memory_order_acquire) &&
            StereoAllowed.load(std::memory_order_acquire) &&
            !RecoveryPending.load(std::memory_order_acquire);
    }
}
