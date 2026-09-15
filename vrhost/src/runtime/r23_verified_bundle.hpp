#pragma once

#include <atomic>
#include <cstdint>

#include "sbs_capture_override.hpp"
#include "vr_shared.hpp"

namespace OutRunVrR23VerifiedBundle
{
    enum class SourceKind : std::uint32_t
    {
        None = 0,
        ClassicSbs = 1,
        DirectGpu = 2,
    };

    struct Snapshot
    {
        std::uint32_t frameId{};
        std::uint32_t poseSequence{};
        std::int64_t presentQpc{};
        std::int64_t sourceCaptureQpc{};
        SourceKind kind{ SourceKind::None };
    };

    inline std::atomic<std::uint32_t> FrameId{ 0 };
    inline std::atomic<std::uint32_t> PoseSequence{ 0 };
    inline std::atomic<std::int64_t> PresentQpc{ 0 };
    inline std::atomic<std::int64_t> SourceCaptureQpc{ 0 };
    inline std::atomic<std::uint32_t> Kind{ static_cast<std::uint32_t>(SourceKind::None) };
    inline std::atomic<std::uint32_t> PublishSequence{ 0 };

    inline void Invalidate() noexcept
    {
        PublishSequence.fetch_add(1, std::memory_order_acq_rel);
        Kind.store(static_cast<std::uint32_t>(SourceKind::None), std::memory_order_relaxed);
        FrameId.store(0, std::memory_order_relaxed);
        PoseSequence.store(0, std::memory_order_relaxed);
        PresentQpc.store(0, std::memory_order_relaxed);
        SourceCaptureQpc.store(0, std::memory_order_relaxed);
        PublishSequence.fetch_add(1, std::memory_order_release);
    }

    inline void Publish(const OutRunVR::SharedRenderFrameState& frame,
        SourceKind kind, std::int64_t sourceCaptureQpc = 0) noexcept
    {
        // main_r23 publishes the production capture before it promotes a classic
        // candidate. When the caller does not pass the QPC explicitly, snapshot
        // the exact R19 production source that is current at this transaction.
        if (kind == SourceKind::ClassicSbs && sourceCaptureQpc <= 0)
            sourceCaptureQpc = OutRunVrSbsCaptureOverride::LastProductionPresentQpc;

        PublishSequence.fetch_add(1, std::memory_order_acq_rel);
        FrameId.store(frame.frameId, std::memory_order_relaxed);
        PoseSequence.store(frame.sourcePoseSequence, std::memory_order_relaxed);
        PresentQpc.store(frame.presentQpc, std::memory_order_relaxed);
        SourceCaptureQpc.store(sourceCaptureQpc, std::memory_order_relaxed);
        Kind.store(static_cast<std::uint32_t>(kind), std::memory_order_relaxed);
        PublishSequence.fetch_add(1, std::memory_order_release);
    }

    inline bool Read(Snapshot& out) noexcept
    {
        for (int attempt = 0; attempt < 4; ++attempt)
        {
            const std::uint32_t before = PublishSequence.load(std::memory_order_acquire);
            if (before & 1u) continue;
            Snapshot s{};
            s.frameId = FrameId.load(std::memory_order_relaxed);
            s.poseSequence = PoseSequence.load(std::memory_order_relaxed);
            s.presentQpc = PresentQpc.load(std::memory_order_relaxed);
            s.sourceCaptureQpc = SourceCaptureQpc.load(std::memory_order_relaxed);
            s.kind = static_cast<SourceKind>(Kind.load(std::memory_order_relaxed));
            const std::uint32_t after = PublishSequence.load(std::memory_order_acquire);
            if (before == after && !(after & 1u))
            {
                out = s;
                return true;
            }
        }
        return false;
    }

    inline bool Matches(const OutRunVR::SharedRenderFrameState& frame,
        SourceKind requiredKind, Snapshot* snapshot = nullptr) noexcept
    {
        Snapshot s{};
        if (!Read(s)) return false;
        const bool match = s.kind == requiredKind && s.frameId != 0 &&
            s.frameId == frame.frameId && s.poseSequence == frame.sourcePoseSequence &&
            s.presentQpc == frame.presentQpc;
        if (match && snapshot) *snapshot = s;
        return match;
    }
}
