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
        "R32-direct-single-projection-async-ack-20260917";

    struct PendingAck
    {
        ID3D11Query* fence = nullptr;
        bool armed = false;
        OutRunVR::SharedRenderFrameState frame{};
    };

    inline std::array<PendingAck, OutRunVR::RenderFrameRingSize> Pending{};
    inline std::uint64_t FastDirectSubmits = 0;
    inline std::uint64_t FastDirectRejects = 0;
    inline std::uint64_t AckArmed = 0;
    inline std::uint64_t AckCompleted = 0;
    inline std::uint64_t AckPublishRetry = 0;
    inline std::uint64_t AckSlotBusy = 0;
    inline ULONGLONG LastPerfLogMs = 0;
    inline bool FirstFastSubmitLogged = false;
    inline bool FirstAsyncAckLogged = false;

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
            pending.frame = {};
        }
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
            if (hr != S_OK)
                continue;
            if (!OutRunVrD3D9ExDirectPassthrough::PublishCompletedFrame(
                    pending.frame))
            {
                ++AckPublishRetry;
                continue;
            }
            pending.armed = false;
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
        if (slot >= Pending.size() || !EnsureFence(slot))
            return false;

        auto& pending = Pending[slot];
        if (pending.armed)
        {
            // Poll once more after all rendering for this frame was queued.
            PollCompletedAcks();
            if (pending.armed)
            {
                ++AckSlotBusy;
                return false;
            }
        }

        OutRunVrFinalTest::Context->End(pending.fence);
        OutRunVrFinalTest::Context->Flush();
        pending.frame = frame;
        pending.armed = true;
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

        const auto state =
            OutRunVrR21RuntimeHardening::ReadDirectHostStateReadonly();
        return OutRunVrR22RuntimeHardening::DirectOpenMatchesLatest(
            state, verified.frame);
    }

    inline void MaybeLogPerf() noexcept
    {
        const ULONGLONG now = GetTickCount64();
        if (LastPerfLogMs == 0)
        {
            LastPerfLogMs = now;
            return;
        }
        if (now - LastPerfLogMs < 5000)
            return;
        LastPerfLogMs = now;
        std::cerr
            << "[R32 direct PERF] fastSubmit=" << FastDirectSubmits
            << " reject=" << FastDirectRejects
            << " ackArmed=" << AckArmed
            << " ackCompleted=" << AckCompleted
            << " ackRetry=" << AckPublishRetry
            << " ackSlotBusy=" << AckSlotBusy
            << " safeCacheHit="
            << OutRunVrD3D9ExDirectPassthrough::R32SharedCacheHits
            << " safeCacheMiss="
            << OutRunVrD3D9ExDirectPassthrough::R32SharedCacheMisses
            << " safeSwap="
            << OutRunVrD3D9ExDirectPassthrough::R32SafeSwaps
            << " timeoutPreserve="
            << OutRunVrD3D9ExDirectPassthrough::R32SafeTimeoutPreserves
            << "\n";
    }

    inline XrResult XRAPI_CALL EndFrame(
        XrSession session, const XrFrameEndInfo* endInfo) noexcept
    {
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
