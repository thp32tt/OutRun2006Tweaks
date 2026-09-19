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
        "R32-direct-single-projection-async-ack-review2-20260917";

    struct PendingAck
    {
        ID3D11Query* fence = nullptr;
        bool armed = false;
        bool flushIssued = false;
        OutRunVR::SharedRenderFrameState frame{};
    };

    inline std::array<PendingAck, OutRunVR::RenderFrameRingSize> Pending{};
    inline std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> AckedFrame{};
    inline std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> AckedGeneration{};
    inline std::uint64_t FastDirectSubmits = 0;
    inline std::uint64_t FastDirectRejects = 0;
    inline std::uint64_t AckArmed = 0;
    inline std::uint64_t AckCompleted = 0;
    inline std::uint64_t AckPublishRetry = 0;
    inline std::uint64_t AckSlotBusy = 0;
    inline std::uint64_t AckFlushEscalations = 0;
    inline std::uint64_t AckQueryErrors = 0;
    inline std::uint32_t AckFaultGeneration = 0;
    inline std::uint32_t ActiveAckGeneration = 0;
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
        AckedFrame.fill(0);
        AckedGeneration.fill(0);
        AckFaultGeneration = 0;
        ActiveAckGeneration = 0;
    }

    inline void ObserveGeneration(std::uint32_t generation) noexcept
    {
        if (!generation || ActiveAckGeneration == generation)
            return;
        ActiveAckGeneration = generation;
        AckedFrame.fill(0);
        AckedGeneration.fill(0);
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

    inline void PollCompletedAcks() noexcept
    {
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
                const std::uint32_t generation =
                    pending.frame.reserved[
                        OutRunVR::RenderFrameDirectGenerationIndex];
                if (generation)
                    AckFaultGeneration = generation;
                ++AckQueryErrors;
                pending.armed = false;
                pending.flushIssued = false;
                pending.frame = {};
                pending.fence->Release();
                pending.fence = nullptr;
                continue;
            }
            const std::uint32_t completedGeneration =
                pending.frame.reserved[
                    OutRunVR::RenderFrameDirectGenerationIndex];
            if (ActiveAckGeneration != 0 &&
                completedGeneration != ActiveAckGeneration)
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
                AckedGeneration[slot] = generation;
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

        if (AckedGeneration[slot] == generation &&
            AckedFrame[slot] == frame.frameId)
            return true;
        if (AckedGeneration[slot] != 0 && AckedGeneration[slot] != generation)
        {
            AckedGeneration[slot] = 0;
            AckedFrame[slot] = 0;
        }

        auto& pending = Pending[slot];
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

        if (AckedGeneration[slot] == generation &&
            AckedFrame[slot] == frame.frameId)
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
        OutRunVrR23VerifiedBundle::Snapshot& verified) noexcept
    {
        using OutRunVrR23VerifiedBundle::SourceKind;
        if (!endInfo ||
            OutRunVrR26RecenterHardening::PendingFocusRecenter ||
            OutRunVrR26RecenterHardening::PendingGameRequestId.load(
                std::memory_order_acquire) != 0 ||
            OutRunVrReviewHardening::HasIncomingNonProjectionLayer(endInfo) ||
            !OutRunVrR23VerifiedBundle::ReadFresh(verified) ||
            verified.kind != SourceKind::DirectGpu ||
            !OutRunVrSbsCaptureOverride::FrameComplete(verified.frame) ||
            !MetadataValid(verified.frame) ||
            !OutRunVrR24BlackScreenGuard::ProjectionMatchesSnapshot(
                endInfo, verified) ||
            !OutRunVrR21RuntimeHardening::DirectTransportRequested())
            return false;

        const std::uint32_t generation =
            verified.frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        if (generation != 0 && AckFaultGeneration == generation)
            return false;

        const auto state =
            OutRunVrR21RuntimeHardening::ReadDirectHostStateReadonly();
        return OutRunVrR22RuntimeHardening::DirectOpenMatchesLatest(
            state, verified.frame);
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
            ObserveGeneration(observed.frame.reserved[
                OutRunVR::RenderFrameDirectGenerationIndex]);
        }
        PollCompletedAcks();

        OutRunVrR23VerifiedBundle::Snapshot verified{};
        if (CanFastSubmit(endInfo, verified) &&
            ArmConsumptionFence(verified.frame))
        {
            const XrResult result =
                OutRunVrFinalTest::EndFrame(session, endInfo);
            const bool submitted = XR_SUCCEEDED(result) &&
                endInfo && endInfo->layerCount > 0;
            OutRunVrR23RuntimeHardening::RecordFinalSubmission(
                verified.frameId, verified.kind, submitted);
            ++FastDirectSubmits;
            if (!FirstFastSubmitLogged)
            {
                FirstFastSubmitLogged = true;
                std::cerr
                    << "[R32 direct] verified incoming DirectGPU projection submitted once; redundant SafeEye copy + second projection removed build="
                    << BuildId << "\n";
            }
            MaybeLogPerf();
            return result;
        }

        if (verified.kind == OutRunVrR23VerifiedBundle::SourceKind::DirectGpu)
            ++FastDirectRejects;
        const XrResult result =
            OutRunVrR26RecenterHardening::EndFrame(session, endInfo);
        MaybeLogPerf();
        return result;
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session) noexcept
    {
        ReleasePending();
        OutRunVrD3D9ExDirectPassthrough::R32ResetDirectCaches();
        return OutRunVrR24BlackScreenGuard::DestroySession(session);
    }
}

#ifdef EnsureSafeFrame
#undef EnsureSafeFrame
#endif
#define xrEndFrame OutRunVrR32DirectSubmit::EndFrame
#define xrDestroySession OutRunVrR32DirectSubmit::DestroySession