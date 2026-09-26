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

    struct ProducerFrameIdentity
    {
        std::uint32_t frameId = 0;
        std::uint32_t clientPid = 0;
        std::uint32_t runGeneration = 0;
        std::uint32_t transportGeneration = 0;
    };

    constexpr bool ExactProducerFrameIdentityMatches(
        const ProducerFrameIdentity& owned,
        const ProducerFrameIdentity& requested) noexcept
    {
        return owned.frameId != 0 &&
            owned.clientPid != 0 &&
            owned.runGeneration != 0 &&
            owned.transportGeneration != 0 &&
            requested.frameId != 0 &&
            requested.clientPid != 0 &&
            requested.runGeneration != 0 &&
            requested.transportGeneration != 0 &&
            owned.frameId == requested.frameId &&
            owned.clientPid == requested.clientPid &&
            owned.runGeneration == requested.runGeneration &&
            owned.transportGeneration == requested.transportGeneration;
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

    enum class PendingFenceDecision : std::uint8_t
    {
        ReuseSlot,
        BlockReuse,
        QueryError
    };

    constexpr PendingFenceDecision ClassifyPendingFence(
        bool pending, bool queryExists, bool queryComplete,
        bool queryStillPending) noexcept
    {
        if (!pending)
            return PendingFenceDecision::ReuseSlot;
        if (!queryExists)
            return PendingFenceDecision::QueryError;
        if (queryComplete)
            return PendingFenceDecision::ReuseSlot;
        return queryStillPending
            ? PendingFenceDecision::BlockReuse
            : PendingFenceDecision::QueryError;
    }
}
