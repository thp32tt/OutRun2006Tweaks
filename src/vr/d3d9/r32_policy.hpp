#pragma once

#include <cstdint>
#include <limits>

namespace OutRunVR::R32
{
    inline constexpr std::uint64_t ResetMonoSafetyPresents = 2;
    inline constexpr std::uint64_t ProducerFenceBudgetMs = 2;

    constexpr std::uint64_t RearmMonoSafetyEpoch(
        std::uint64_t presentEpoch,
        std::uint64_t extraPresents = ResetMonoSafetyPresents) noexcept
    {
        if (presentEpoch == 0)
            presentEpoch = 1;
        const auto maxValue = (std::numeric_limits<std::uint64_t>::max)();
        return extraPresents > maxValue - presentEpoch
            ? maxValue
            : presentEpoch + extraPresents;
    }

    enum class EffectSnapshotDecision : std::uint8_t
    {
        UseCapturedPolicy,
        ForceZeroDisparity
    };

    constexpr EffectSnapshotDecision EffectSnapshotResult(
        bool allReadsSucceeded) noexcept
    {
        return allReadsSucceeded
            ? EffectSnapshotDecision::UseCapturedPolicy
            : EffectSnapshotDecision::ForceZeroDisparity;
    }
}
