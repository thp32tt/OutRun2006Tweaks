#pragma once

#include <atomic>
#include <cstdint>

#include "vr_shared.hpp"

namespace OutRunVrR23VerifiedBundle
{
    enum class SourceKind : std::uint32_t
    {
        None = 0,
        ClassicSbs = 1,
        DirectGpu = 2,
    };

    inline std::atomic<std::uint32_t> FrameId{ 0 };
    inline std::atomic<std::uint32_t> PoseSequence{ 0 };
    inline std::atomic<std::int64_t> PresentQpc{ 0 };
    inline std::atomic<std::uint32_t> Kind{ static_cast<std::uint32_t>(SourceKind::None) };
    inline std::atomic<std::uint32_t> PublishSequence{ 0 };

    inline void Invalidate() noexcept
    {
        PublishSequence.fetch_add(1, std::memory_order_acq_rel);
        Kind.store(static_cast<std::uint32_t>(SourceKind::None), std::memory_order_relaxed);
        FrameId.store(0, std::memory_order_relaxed);
        PoseSequence.store(0, std::memory_order_relaxed);
        PresentQpc.store(0, std::memory_order_relaxed);
        PublishSequence.fetch_add(1, std::memory_order_release);
    }

    inline void Publish(const OutRunVR::SharedRenderFrameState& frame, SourceKind kind) noexcept
    {
        PublishSequence.fetch_add(1, std::memory_order_acq_rel);
        FrameId.store(frame.frameId, std::memory_order_relaxed);
        PoseSequence.store(frame.sourcePoseSequence, std::memory_order_relaxed);
        PresentQpc.store(frame.presentQpc, std::memory_order_relaxed);
        Kind.store(static_cast<std::uint32_t>(kind), std::memory_order_relaxed);
        PublishSequence.fetch_add(1, std::memory_order_release);
    }

    inline bool Matches(const OutRunVR::SharedRenderFrameState& frame, SourceKind requiredKind) noexcept
    {
        for (int attempt = 0; attempt < 4; ++attempt)
        {
            const std::uint32_t before = PublishSequence.load(std::memory_order_acquire);
            if (before & 1u)
                continue;
            const auto frameId = FrameId.load(std::memory_order_relaxed);
            const auto poseSequence = PoseSequence.load(std::memory_order_relaxed);
            const auto presentQpc = PresentQpc.load(std::memory_order_relaxed);
            const auto kind = Kind.load(std::memory_order_relaxed);
            const std::uint32_t after = PublishSequence.load(std::memory_order_acquire);
            if (before != after || (after & 1u))
                continue;
            return kind == static_cast<std::uint32_t>(requiredKind) &&
                frameId != 0 && frameId == frame.frameId &&
                poseSequence == frame.sourcePoseSequence &&
                presentQpc == frame.presentQpc;
        }
        return false;
    }
}
