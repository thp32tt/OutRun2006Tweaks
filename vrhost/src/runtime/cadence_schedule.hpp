#pragma once
// R35 frame pacing: advance the OpenXR display-time deadline in O(1).
// A suspended runtime can advance predictedDisplayTime by hours; iterating one
// nominal game period at a time would wedge the host (and headset compositor).
// Rebase only on a large *backwards* clock discontinuity, not normal XR jitter.
#include <cstdint>
#include <limits>

namespace OutRunVR::CadenceSchedule
{
    // The display deadline, refresh EWMA and target-rate debounce belong to
    // one OpenXR session. Carrying them across STOPPING -> READY can discard
    // the first game presents, especially when the runtime changes Hz/epoch.
    struct SessionEpoch
    {
        std::int64_t nextRequestDisplayTime{};
        float activeRenderHz{};
        float pendingRenderHz{};
        std::uint32_t pendingRenderHzSamples{};
        double actualXrHz{};
        double actualDisplayPeriodMs{};
        double lastLoggedXrHz{};

        constexpr bool OnRunningTransition(bool previouslyRunning,
            bool running) noexcept
        {
            if (previouslyRunning == running)
                return false;
            *this = {};
            return true;
        }
    };

    struct Decision
    {
        std::int64_t nextDisplayTime{};
        bool issue{};
    };

    inline constexpr std::int64_t BackwardDiscontinuityNs = 1'000'000'000;

    constexpr Decision Advance(std::int64_t predictedDisplayTime,
        std::int64_t gamePeriod, std::int64_t nextDisplayTime) noexcept
    {
        if (predictedDisplayTime <= 0 || gamePeriod <= 0)
            return {nextDisplayTime, false};

        // xrWaitFrame may restart its display-time epoch after a session/loss
        // transition. Do not suppress every game frame until the old epoch
        // finally catches up. Ordinary early ticks retain the phase schedule.
        if (nextDisplayTime <= 0 ||
            (predictedDisplayTime < nextDisplayTime &&
             nextDisplayTime - predictedDisplayTime > BackwardDiscontinuityNs))
            nextDisplayTime = predictedDisplayTime;

        if (predictedDisplayTime < nextDisplayTime)
            return {nextDisplayTime, false};

        const auto missed = static_cast<std::uint64_t>(
            predictedDisplayTime - nextDisplayTime);
        const auto steps = missed / static_cast<std::uint64_t>(gamePeriod) + 1u;
        const auto capacity = static_cast<std::uint64_t>(
            std::numeric_limits<std::int64_t>::max() - nextDisplayTime);
        if (steps > capacity / static_cast<std::uint64_t>(gamePeriod))
        {
            // An XrTime extremely near INT64_MAX has no representable future
            // deadline. Avoid signed overflow while preserving the next tick.
            return {std::numeric_limits<std::int64_t>::max(), true};
        }
        return {nextDisplayTime +
            static_cast<std::int64_t>(steps *
                static_cast<std::uint64_t>(gamePeriod)), true};
    }
}
