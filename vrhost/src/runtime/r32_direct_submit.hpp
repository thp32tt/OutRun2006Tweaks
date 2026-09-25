#pragma once

// R32 final DirectGPU submission fast path.
//
// main_r23 already rendered a validated DirectGPU source into the incoming
// OpenXR projection before xrEndFrame. R24 deliberately rebuilt that image from
// SafeEye, which added two full-eye CopyResource operations, a synchronous 8 ms
// fence budget and a second pair of projection blits. R32 submits the already
// verified incoming projection once and places a D3D11 EVENT after the source
// sampling commands. Producer-ring ACK is published asynchronously only after
// that event completes. Any uncertainty falls through to R26/R24, preserving
// SafeEye A/B and visible fallback behavior.
//
// Review-2 hardening removes the unconditional per-frame D3D11 Flush. A Flush is
// issued only when a producer slot is actually blocked by a still-pending ACK,
// so normal command batching is preserved without weakening reuse safety.

#include "r26_recenter_hardening.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif
#ifdef xrDestroySession
#undef xrDestroySession
#endif

#include <array>
#include <cstdint>
#include <iostream>

namespace OutRunVrR32DirectSubmit
{
    inline constexpr const char* BuildId =
        "R45-direct-recenter-live-projection-20260920";

    enum class FastRejectReason : std::uint8_t
    {
        None,
        NoEndInfo,
        PendingRecenter,
        PendingGameRequest,
        NonProjectionLayer,
        BundleNotFresh,
        NotDirectGpu,
        FrameIncomplete,
        MetadataInvalid,
        ProjectionMismatch,
        TransportDisabled,
        GenerationFault,
        AckBusy,
        Count
    };

    struct PendingAck
    {
        ID3D11Query* fence = nullptr;
        bool armed = false;
        bool flushIssued = false;
        OutRunVR::SharedRenderFrameState frame{};
    };

    struct PendingSkippedRelease
    {
        bool pending = false;
        OutRunVR::SharedRenderFrameState frame{};
    };

    inline std::array<PendingAck, OutRunVR::RenderFrameRingSize> Pending{};
    inline std::array<PendingSkippedRelease, OutRunVR::RenderFrameRingSize>
        SkippedRelease{};

    struct AckIdentity
    {
        std::uint32_t clientPid = 0;
        std::uint32_t runGeneration = 0;
        std::uint32_t transportGeneration = 0;
    };

    inline AckIdentity FrameAckIdentity(
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        return {
            frame.clientPid,
            frame.reserved[OutRunVR::RenderFrameRunGenerationIndex],
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex]
        };
    }

    inline bool SameAckIdentity(
        const AckIdentity& a, const AckIdentity& b) noexcept
    {
        return a.clientPid != 0 &&
            a.runGeneration != 0 &&
            a.transportGeneration != 0 &&
            a.clientPid == b.clientPid &&
            a.runGeneration == b.runGeneration &&
            a.transportGeneration == b.transportGeneration;
    }

    inline bool SameFrameAckIdentity(
        const OutRunVR::SharedRenderFrameState& a,
        const OutRunVR::SharedRenderFrameState& b) noexcept
    {
        return a.frameId != 0 &&
            a.frameId == b.frameId &&
            SameAckIdentity(FrameAckIdentity(a), FrameAckIdentity(b));
    }

    inline std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> AckedFrame{};
    inline std::array<AckIdentity, OutRunVR::RenderFrameRingSize> AckedIdentity{};
    inline std::uint64_t FastDirectSubmits = 0;
    inline std::uint64_t FastDirectRejects = 0;
    inline std::uint64_t AckArmed = 0;
    inline std::uint64_t AckCompleted = 0;
    inline std::uint64_t AckPublishRetry = 0;
    inline std::uint64_t AckSlotBusy = 0;
    inline std::uint64_t AckFlushEscalations = 0;
    inline std::uint64_t AckQueryErrors = 0;
    inline std::uint64_t AckSameFramePendingReuse = 0;
    inline std::uint64_t SkippedReleaseQueued = 0;
    inline std::uint64_t SkippedReleaseCompleted = 0;
    inline std::uint64_t SkippedReleaseRetry = 0;
    inline std::array<std::uint64_t,
        static_cast<std::size_t>(FastRejectReason::Count)> RejectReasons{};
    inline AckIdentity AckFaultIdentity{};
    inline AckIdentity ActiveAckIdentity{};
    inline ULONGLONG LastPerfLogMs = 0;
    inline bool FirstFastSubmitLogged = false;
    inline bool FirstAsyncAckLogged = false;
    inline bool FirstDeferredFlushLogged = false;

    struct PerfSnapshot
    {
        std::uint64_t fastSubmit = 0;
        std::uint64_t reject = 0;
        std::uint64_t ackArmed = 0;
        std::uint64_t ackCompleted = 0;
        std::uint64_t ackRetry = 0;
        std::uint64_t ackSlotBusy = 0;
        std::uint64_t flushEscalations = 0;
        std::uint64_t ackQueryError = 0;
        std::uint64_t sameFramePendingReuse = 0;
        std::uint64_t skippedQueued = 0;
        std::uint64_t skippedCompleted = 0;
        std::uint64_t skippedRetry = 0;
        std::array<std::uint64_t,
            static_cast<std::size_t>(FastRejectReason::Count)> rejectReasons{};
        std::uint64_t safeCacheHit = 0;
        std::uint64_t safeCacheMiss = 0;
        std::uint64_t safeSwap = 0;
        std::uint64_t timeoutPreserve = 0;
    };
    inline PerfSnapshot Perf{};

    inline void ReleasePending() noexcept
    {
        for (auto& pending : Pending)
        {
            if (pending.fence)
            {
                pending.fence->Release();
                pending.fence = nullptr;
            }
            pending.armed = false;
            pending.flushIssued = false;
            pending.frame = {};
        }
        for (auto& skipped : SkippedRelease)
        {
            skipped.pending = false;
            skipped.frame = {};
        }
        AckedFrame.fill(0);
        AckedIdentity.fill({});
        AckFaultIdentity = {};
        ActiveAckIdentity = {};
        AckSameFramePendingReuse = 0;
        RejectReasons.fill(0);
    }

    inline void ObserveIdentity(
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        const AckIdentity identity = FrameAckIdentity(frame);
        if (!identity.clientPid || !identity.runGeneration ||
            !identity.transportGeneration)
            return;
        if (SameAckIdentity(ActiveAckIdentity, identity))
            return;

        ActiveAckIdentity = identity;
        AckedFrame.fill(0);
        AckedIdentity.fill({});

        for (auto& skipped : SkippedRelease)
        {
            if (!skipped.pending)
                continue;
            if (!SameAckIdentity(
                    FrameAckIdentity(skipped.frame), identity))
            {
                skipped.pending = false;
                skipped.frame = {};
            }
        }

        // Query failure quarantine belongs to one exact producer run. A new
        // game run must not inherit a colliding transport-generation fault.
        if (!SameAckIdentity(AckFaultIdentity, identity))
            AckFaultIdentity = {};
    }

    inline bool EnsureFence(std::uint32_t slot) noexcept
    {
        if (slot >= Pending.size() || !OutRunVrFinalTest::Device)
            return false;
        auto& pending = Pending[slot];
        if (pending.fence)
            return true;
        D3D11_QUERY_DESC desc{};
        desc.Query = D3D11_QUERY_EVENT;
        return SUCCEEDED(OutRunVrFinalTest::Device->CreateQuery(
            &desc, &pending.fence)) && pending.fence;
    }

    inline bool HasPendingConsumption(
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        const std::uint32_t slot =
            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const AckIdentity identity = FrameAckIdentity(frame);
        if (slot >= Pending.size() || !identity.clientPid ||
            !identity.runGeneration || !identity.transportGeneration ||
            !frame.frameId)
            return false;
        const auto& pending = Pending[slot];
        return pending.armed &&
            SameFrameAckIdentity(pending.frame, frame);
    }

    inline bool QueueSkippedRelease(
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        const std::uint32_t slot =
            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const AckIdentity identity = FrameAckIdentity(frame);
        if (slot >= SkippedRelease.size() || !identity.clientPid ||
            !identity.runGeneration || !identity.transportGeneration ||
            !frame.frameId)
            return false;
        if (ActiveAckIdentity.clientPid != 0 &&
            !SameAckIdentity(identity, ActiveAckIdentity))
            return false;

        if (HasPendingConsumption(frame))
            return false;

        if (OutRunVrD3D9ExDirectPassthrough::PublishCompletedFrame(frame))
        {
            AckedFrame[slot] = frame.frameId;
            AckedIdentity[slot] = identity;
            ++SkippedReleaseCompleted;
            return true;
        }

        auto& skipped = SkippedRelease[slot];
        if (skipped.pending)
        {
            // Never overwrite a still-current release owner for the same slot.
            // If it belongs to an obsolete game run, it can be retired now.
            if (OutRunVrD3D9ExDirectPassthrough::FrameRunIdentityCurrent(
                    skipped.frame))
            {
                ++SkippedReleaseRetry;
                return false;
            }
            skipped.pending = false;
            skipped.frame = {};
        }

        skipped.pending = true;
        skipped.frame = frame;
        ++SkippedReleaseQueued;
        return false;
    }

    inline void PollSkippedReleases() noexcept
    {
        for (std::size_t slot = 0; slot < SkippedRelease.size(); ++slot)
        {
            auto& skipped = SkippedRelease[slot];
            if (!skipped.pending)
                continue;
            const AckIdentity identity =
                FrameAckIdentity(skipped.frame);
            if ((ActiveAckIdentity.clientPid != 0 &&
                 !SameAckIdentity(identity, ActiveAckIdentity)) ||
                !OutRunVrD3D9ExDirectPassthrough::FrameRunIdentityCurrent(
                    skipped.frame))
            {
                skipped.pending = false;
                skipped.frame = {};
                continue;
            }
            if (!OutRunVrD3D9ExDirectPassthrough::PublishCompletedFrame(
                    skipped.frame))
            {
                ++SkippedReleaseRetry;
                continue;
            }

            AckedFrame[slot] = skipped.frame.frameId;
            AckedIdentity[slot] = FrameAckIdentity(skipped.frame);
            skipped.pending = false;
            skipped.frame = {};
            ++SkippedReleaseCompleted;
        }
    }

    inline void PollCompletedAcks() noexcept
    {
        // Skipped frames never touched D3D11, so their ACK retry does not
        // require a graphics context and can still complete during session
        // transitions. Touched frames below remain EVENT-gated.
        PollSkippedReleases();
        if (!OutRunVrFinalTest::Context)
            return;
        for (auto& pending : Pending)
        {
            if (!pending.armed || !pending.fence)
                continue;
            const HRESULT hr = OutRunVrFinalTest::Context->GetData(
                pending.fence, nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
            if (hr == S_FALSE)
                continue;
            if (FAILED(hr))
            {
                // Completion is unknowable, so never ACK this producer frame.
                // Disable fast-submit for its transport generation and let the
                // SafeEye fallback perform a separately fenced copy/ACK.
                const AckIdentity identity =
                    FrameAckIdentity(pending.frame);
                if (identity.clientPid && identity.runGeneration &&
                    identity.transportGeneration)
                    AckFaultIdentity = identity;
                ++AckQueryErrors;
                pending.armed = false;
                pending.flushIssued = false;
                pending.frame = {};
                pending.fence->Release();
                pending.fence = nullptr;
                continue;
            }
            const AckIdentity completedIdentity =
                FrameAckIdentity(pending.frame);
            if (ActiveAckIdentity.clientPid != 0 &&
                !SameAckIdentity(completedIdentity, ActiveAckIdentity))
            {
                // Late completion from a superseded shared-eye generation is
                // safe to forget, but must never roll the global ACK generation
                // backwards and stall the producer's new ring.
                pending.armed = false;
                pending.flushIssued = false;
                pending.frame = {};
                ++AckCompleted;
                continue;
            }
            if (!OutRunVrD3D9ExDirectPassthrough::FrameRunIdentityCurrent(
                    pending.frame))
            {
                // A new game process has claimed Frame.v2. This completed fence
                // belongs to an old producer run and must not rewrite the ACK
                // mapping or remain as an infinite retry owner.
                pending.armed = false;
                pending.flushIssued = false;
                pending.frame = {};
                ++AckCompleted;
                continue;
            }
            if (!OutRunVrD3D9ExDirectPassthrough::PublishCompletedFrame(
                    pending.frame))
            {
                ++AckPublishRetry;
                continue;
            }
            const std::uint32_t slot =
                pending.frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
            const std::uint32_t generation =
                pending.frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
            if (slot < AckedFrame.size())
            {
                AckedFrame[slot] = pending.frame.frameId;
                AckedIdentity[slot] = FrameAckIdentity(pending.frame);
            }
            pending.armed = false;
            pending.flushIssued = false;
            pending.frame = {};
            ++AckCompleted;
            if (!FirstAsyncAckLogged)
            {
                FirstAsyncAckLogged = true;
                std::cerr
                    << "[R32 direct] asynchronous GPU-consumption ACK active; producer slots are released without an xrEndFrame CPU fence wait\n";
            }
        }
    }

    inline bool ArmConsumptionFence(
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        if (!OutRunVrFinalTest::Context)
            return false;
        const std::uint32_t slot =
            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const std::uint32_t generation =
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        if (slot >= Pending.size() || !generation || !EnsureFence(slot))
            return false;

        const AckIdentity identity = FrameAckIdentity(frame);
        if (AckedFrame[slot] == frame.frameId &&
            SameAckIdentity(AckedIdentity[slot], identity))
            return true;
        if (AckedIdentity[slot].clientPid != 0 &&
            !SameAckIdentity(AckedIdentity[slot], identity))
        {
            AckedIdentity[slot] = {};
            AckedFrame[slot] = 0;
        }

        auto& pending = Pending[slot];
        if (pending.armed &&
            SameFrameAckIdentity(pending.frame, frame))
        {
            // R42: xrWaitFrame can submit the same already-rendered projection
            // more than once before the first EVENT is observed complete. The
            // existing EVENT already protects the only shared-source sampling
            // commands for this producer frame, so do not demote a harmless
            // cached projection tick into the synchronous SafeEye fallback.
            ++AckSameFramePendingReuse;
            return true;
        }
        if (pending.armed)
        {
            PollCompletedAcks();
            if (pending.armed && !pending.flushIssued)
            {
                OutRunVrFinalTest::Context->Flush();
                pending.flushIssued = true;
                ++AckFlushEscalations;
                if (!FirstDeferredFlushLogged)
                {
                    FirstDeferredFlushLogged = true;
                    std::cerr
                        << "[R32 direct] D3D11 Flush is deferred until actual direct-ring slot pressure; steady frames keep driver batching intact\n";
                }
                PollCompletedAcks();
            }
            if (pending.armed)
            {
                ++AckSlotBusy;
                return false;
            }
        }

        if (AckedFrame[slot] == frame.frameId &&
            SameAckIdentity(AckedIdentity[slot], identity))
            return true;

        OutRunVrFinalTest::Context->End(pending.fence);
        pending.frame = frame;
        pending.armed = true;
        pending.flushIssued = false;
        ++AckArmed;
        return true;
    }

    inline bool MetadataValid(
        const OutRunVR::SharedRenderFrameState& frame) noexcept
    {
        const std::uint32_t slot =
            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const std::uint32_t generation =
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        const std::uint32_t width =
            frame.reserved[OutRunVR::RenderFrameDirectWidthIndex];
        const std::uint32_t height =
            frame.reserved[OutRunVR::RenderFrameDirectHeightIndex];
        const auto format =
            OutRunVrD3D9ExDirectPassthrough::ExpectedDeclaredFormat(
                frame.reserved[OutRunVR::RenderFrameDirectFormatIndex]);
        return slot < Pending.size() && generation != 0 && width != 0 &&
            height != 0 && width == frame.backbufferWidth &&
            height == frame.backbufferHeight && format != DXGI_FORMAT_UNKNOWN;
    }

    inline bool CanFastSubmit(
        const XrFrameEndInfo* endInfo,
        OutRunVrR23VerifiedBundle::Snapshot& verified,
        FastRejectReason& reject) noexcept
    {
        using OutRunVrR23VerifiedBundle::SourceKind;
        reject = FastRejectReason::None;
        if (!endInfo) { reject = FastRejectReason::NoEndInfo; return false; }
        if (OutRunVrR26RecenterHardening::PendingFocusRecenter)
        { reject = FastRejectReason::PendingRecenter; return false; }
        // R45: a game recenter request must not disable the only fresh
        // DirectGPU presentation path. R44/R42 fell through to R24 cached-image
        // fallback here; R26 then refused to mark a cached fallback as applied,
        // leaving PendingGameRequestId set forever and permanently disabling
        // fast submit. The synthetic LOCAL-change event is consumed before this
        // frame is rendered, so a successful fresh projection is a valid
        // post-recenter visible submission and completes the request below.
        if (OutRunVrReviewHardening::HasIncomingNonProjectionLayer(endInfo))
        { reject = FastRejectReason::NonProjectionLayer; return false; }
        if (!OutRunVrR23VerifiedBundle::ReadFresh(verified))
        { reject = FastRejectReason::BundleNotFresh; return false; }
        if (verified.kind != SourceKind::DirectGpu)
        { reject = FastRejectReason::NotDirectGpu; return false; }
        if (!OutRunVrSbsCaptureOverride::FrameComplete(verified.frame))
        { reject = FastRejectReason::FrameIncomplete; return false; }
        if (!MetadataValid(verified.frame))
        { reject = FastRejectReason::MetadataInvalid; return false; }
        if (!OutRunVrR24BlackScreenGuard::ProjectionMatchesSnapshot(
                endInfo, verified))
        { reject = FastRejectReason::ProjectionMismatch; return false; }
        if (!OutRunVrR21RuntimeHardening::DirectTransportRequested())
        { reject = FastRejectReason::TransportDisabled; return false; }

        const AckIdentity identity = FrameAckIdentity(verified.frame);
        if (SameAckIdentity(AckFaultIdentity, identity))
        { reject = FastRejectReason::GenerationFault; return false; }

        // main_r23 has already staged this exact immutable slot and rendered the
        // verified projection. R42 permits repeated submission of that same
        // projection while its original async EVENT is still pending.
        return true;
    }

    inline void CapturePerfSnapshot() noexcept
    {
        Perf.fastSubmit = FastDirectSubmits;
        Perf.reject = FastDirectRejects;
        Perf.ackArmed = AckArmed;
        Perf.ackCompleted = AckCompleted;
        Perf.ackRetry = AckPublishRetry;
        Perf.ackSlotBusy = AckSlotBusy;
        Perf.flushEscalations = AckFlushEscalations;
        Perf.ackQueryError = AckQueryErrors;
        Perf.sameFramePendingReuse = AckSameFramePendingReuse;
        Perf.skippedQueued = SkippedReleaseQueued;
        Perf.skippedCompleted = SkippedReleaseCompleted;
        Perf.skippedRetry = SkippedReleaseRetry;
        Perf.rejectReasons = RejectReasons;
        Perf.safeCacheHit = OutRunVrD3D9ExDirectPassthrough::R32SharedCacheHits;
        Perf.safeCacheMiss = OutRunVrD3D9ExDirectPassthrough::R32SharedCacheMisses;
        Perf.safeSwap = OutRunVrD3D9ExDirectPassthrough::R32SafeSwaps;
        Perf.timeoutPreserve = OutRunVrD3D9ExDirectPassthrough::R32SafeTimeoutPreserves;
    }

    inline void MaybeLogPerf() noexcept
    {
        const ULONGLONG now = GetTickCount64();
        if (LastPerfLogMs == 0)
        {
            LastPerfLogMs = now;
            CapturePerfSnapshot();
            return;
        }
        if (now - LastPerfLogMs < 5000)
            return;
        LastPerfLogMs = now;
        std::cerr
            << "[R32 direct PERF 5s] fastSubmit=" << FastDirectSubmits - Perf.fastSubmit
            << " reject=" << FastDirectRejects - Perf.reject
            << " ackArmed=" << AckArmed - Perf.ackArmed
            << " ackCompleted=" << AckCompleted - Perf.ackCompleted
            << " ackRetry=" << AckPublishRetry - Perf.ackRetry
            << " ackSlotBusy=" << AckSlotBusy - Perf.ackSlotBusy
            << " deferredFlush=" << AckFlushEscalations - Perf.flushEscalations
            << " ackQueryError=" << AckQueryErrors - Perf.ackQueryError
            << " sameFrameAckReuse="
            << AckSameFramePendingReuse - Perf.sameFramePendingReuse
            << " skippedAck[queued="
            << SkippedReleaseQueued - Perf.skippedQueued
            << ",completed="
            << SkippedReleaseCompleted - Perf.skippedCompleted
            << ",retry="
            << SkippedReleaseRetry - Perf.skippedRetry
            << "]"
            << " rejectReason[projection="
            << RejectReasons[static_cast<std::size_t>(
                FastRejectReason::ProjectionMismatch)] -
               Perf.rejectReasons[static_cast<std::size_t>(
                FastRejectReason::ProjectionMismatch)]
            << ",ackBusy="
            << RejectReasons[static_cast<std::size_t>(
                FastRejectReason::AckBusy)] -
               Perf.rejectReasons[static_cast<std::size_t>(
                FastRejectReason::AckBusy)]
            << ",bundle="
            << RejectReasons[static_cast<std::size_t>(
                FastRejectReason::BundleNotFresh)] -
               Perf.rejectReasons[static_cast<std::size_t>(
                FastRejectReason::BundleNotFresh)]
            << ",recenter="
            << RejectReasons[static_cast<std::size_t>(
                FastRejectReason::PendingRecenter)] -
               Perf.rejectReasons[static_cast<std::size_t>(
                FastRejectReason::PendingRecenter)]
            << "]"
            << " safeCacheHit="
            << OutRunVrD3D9ExDirectPassthrough::R32SharedCacheHits - Perf.safeCacheHit
            << " safeCacheMiss="
            << OutRunVrD3D9ExDirectPassthrough::R32SharedCacheMisses - Perf.safeCacheMiss
            << " safeSwap="
            << OutRunVrD3D9ExDirectPassthrough::R32SafeSwaps - Perf.safeSwap
            << " timeoutPreserve="
            << OutRunVrD3D9ExDirectPassthrough::R32SafeTimeoutPreserves - Perf.timeoutPreserve
            << "\n";
        CapturePerfSnapshot();
    }

    inline XrResult XRAPI_CALL EndFrame(
        XrSession session, const XrFrameEndInfo* endInfo) noexcept
    {
        // Learn the newest committed DirectGPU generation before polling older
        // EVENT queries. This closes the reset/recreation ACK rollback window.
        OutRunVrR23VerifiedBundle::Snapshot observed{};
        if (OutRunVrR23VerifiedBundle::ReadFresh(observed) &&
            observed.kind ==
                OutRunVrR23VerifiedBundle::SourceKind::DirectGpu &&
            MetadataValid(observed.frame))
        {
            ObserveIdentity(observed.frame);
        }
        PollCompletedAcks();

        OutRunVrR23VerifiedBundle::Snapshot verified{};
        FastRejectReason reject = FastRejectReason::None;
        const bool fastEligible = CanFastSubmit(endInfo, verified, reject);
        const bool ackReady =
            fastEligible && ArmConsumptionFence(verified.frame);
        if (fastEligible && ackReady)
        {
            const XrResult result =
                OutRunVrFinalTest::EndFrame(session, endInfo);
            const bool submitted = XR_SUCCEEDED(result) &&
                endInfo && endInfo->layerCount > 0;
            OutRunVrR23RuntimeHardening::RecordFinalSubmission(
                verified.frameId, verified.kind, submitted);
            ++FastDirectSubmits;
            if (submitted)
                OutRunVrR26RecenterHardening::
                    CompletePendingGameRequestAfterVisibleProjection();
            if (!FirstFastSubmitLogged)
            {
                FirstFastSubmitLogged = true;
                std::cerr
                    << "[R32 direct] verified incoming DirectGPU projection submitted once; rendered projection is presentation-authoritative while its exact producer slot stays protected by asynchronous GPU ACK; redundant SafeEye copy + second projection removed; R42 same-frame pending EVENT reuse prevents cached XR ticks from entering SafeEye fallback build="
                    << BuildId << "\n";
            }
            MaybeLogPerf();
            return result;
        }

        if (fastEligible && !ackReady)
            reject = FastRejectReason::AckBusy;
        if (reject != FastRejectReason::None)
        {
            ++FastDirectRejects;
            const auto index = static_cast<std::size_t>(reject);
            if (index < RejectReasons.size())
                ++RejectReasons[index];
        }
        const XrResult result =
            OutRunVrR26RecenterHardening::EndFrame(session, endInfo);
        MaybeLogPerf();
        return result;
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session) noexcept
    {
        // D3D11 EVENT queries protect producer texture reuse, not OpenXR
        // session objects. A STOPPING/loss transition can destroy and recreate
        // the XR session while the same host process/device remains alive.
        // Preserve incomplete EVENT owners across that boundary; completed
        // queries and never-touched skipped releases are retired first.
        PollCompletedAcks();
        OutRunVrD3D9ExDirectPassthrough::R32ResetDirectCaches();
        return OutRunVrR24BlackScreenGuard::DestroySession(session);
    }
}

#ifdef EnsureSafeFrame
#undef EnsureSafeFrame
#endif
#define xrEndFrame OutRunVrR32DirectSubmit::EndFrame
#define xrDestroySession OutRunVrR32DirectSubmit::DestroySession