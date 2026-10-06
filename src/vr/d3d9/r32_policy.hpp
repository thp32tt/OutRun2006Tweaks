#pragma once

#include <cstdint>
#include <limits>

namespace OutRunVR::R32
{
    inline constexpr std::uint64_t ResetMonoSafetyPresents = 2;

    // Diagnostic-only frame-spike thresholds. These do not drive cadence or
    // rendering policy; the relative gate follows the observed runtime baseline
    // so 72/80/90/120 Hz sessions are not treated as one fixed refresh target.
    inline constexpr std::uint64_t PerfSpikeAbsoluteUs = 18000;
    inline constexpr std::uint64_t PerfSpikeHardUs = 30000;
    inline constexpr std::uint64_t PerfSpikeRelativePercent = 130;
    inline constexpr std::uint64_t PerfSpikeLogCooldownMs = 100;

    constexpr bool IsPerfFrameSpike(
        std::uint64_t frameUs,
        std::uint64_t baselineUs) noexcept
    {
        if (frameUs >= PerfSpikeHardUs)
            return true;
        if (frameUs < PerfSpikeAbsoluteUs)
            return false;
        if (baselineUs == 0)
            return true;
        return frameUs * 100 >= baselineUs * PerfSpikeRelativePercent;
    }

    constexpr std::uint64_t UpdatePerfBaselineUs(
        std::uint64_t baselineUs,
        std::uint64_t frameUs,
        bool spike) noexcept
    {
        if (frameUs == 0)
            return baselineUs;
        if (baselineUs == 0)
            return frameUs;
        if (spike)
            return baselineUs;
        return (baselineUs * 31 + frameUs) / 32;
    }

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
