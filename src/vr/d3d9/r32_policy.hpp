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
        // FrameUs is bounded by the hard-spike early return above; a
        // corrupt/stale baseline may not be. Avoid wrapping the RHS and
        // incorrectly reporting a normal frame as a diagnostic spike.
        const auto maxValue = (std::numeric_limits<std::uint64_t>::max)();
        if (baselineUs > maxValue / PerfSpikeRelativePercent)
            return false;
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
        // Exact integer EMA (31*baseline + frame)/32 without overflowing
        // uint64_t on a stale QPC-derived sample. Preserve floor rounding
        // when the new frame is smaller than the current baseline.
        if (frameUs >= baselineUs)
            return baselineUs + (frameUs - baselineUs) / 32;
        const auto drop = baselineUs - frameUs;
        return baselineUs - drop / 32 - (drop % 32 != 0 ? 1 : 0);
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
