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

    // R22/R23 are the final game-side safety overlays. Earlier R20/R21 layers
    // may observe a fresh host or a plausible baseline while those hooks are
    // still being installed, but that must never make stereo/WVP eligible.
    inline std::atomic<bool> SafetyOverlayReady{ false };

    inline void FailClosed() noexcept
    {
        HostFresh.store(false, std::memory_order_release);
        StereoAllowed.store(false, std::memory_order_release);
        RecoveryPending.store(true, std::memory_order_release);
    }

    inline void MarkSafetyOverlayUnavailable() noexcept
    {
        SafetyOverlayReady.store(false, std::memory_order_release);
        FailClosed();
    }

    inline void MarkSafetyOverlayInstalled() noexcept
    {
        // Never inherit a baseline observed before the final R22/R23 callbacks
        // became authoritative. Force one fresh Present + verified baseline
        // after installation before reopening stereo or WVP injection.
        FailClosed();
        SafetyOverlayReady.store(true, std::memory_order_release);
    }

    inline void ObserveFreshHost() noexcept
    {
        HostFresh.store(true, std::memory_order_release);
        // Do not reopen stereo here. A fresh host after a stall still needs a
        // newly verified zero-disparity color/depth baseline before injection.
    }

    inline void BaselineVerified() noexcept
    {
        if (!SafetyOverlayReady.load(std::memory_order_acquire) ||
            !HostFresh.load(std::memory_order_acquire))
            return;
        RecoveryPending.store(false, std::memory_order_release);
        StereoAllowed.store(true, std::memory_order_release);
    }

    inline bool MayInjectStereo() noexcept
    {
        return SafetyOverlayReady.load(std::memory_order_acquire) &&
            HostFresh.load(std::memory_order_acquire) &&
            StereoAllowed.load(std::memory_order_acquire) &&
            !RecoveryPending.load(std::memory_order_acquire);
    }
}
