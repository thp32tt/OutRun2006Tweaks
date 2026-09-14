#pragma once

// R13 arbitration between the R10 Desktop-Duplication fallback and the
// D3D9Ex -> D3D11 shared-eye ring.
//
// R12 proved that an exact hostDirectConsumedFrameId is useful to establish
// that the host opened the exact shared-eye frame, but that ACK happens before
// RenderProjection samples the shared SRVs.  It therefore cannot authorize the
// D3D9 producer to reuse the slot.  R13 adds a second, GPU-completion ACK in
// SharedPoseState::reserved[15].  The game producer uses only that safe ACK for
// ring reuse.

#include "sbs_capture_override.hpp"
#include "../../../src/vr/d3d9/r13_bridge.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif

#include <cstdint>
#include <iostream>

namespace OutRunVrD3D9ExDirectPassthrough
{
    inline constexpr const char* BuildId = "D3D9Ex-direct-passthrough-R13-20260915";
    inline constexpr ULONGLONG FallbackSourceMaxAgeMs = 250;
    inline constexpr ULONGLONG ConsumerFenceTimeoutMs = 25;

    inline std::uint64_t DirectPassFrames = 0;
    inline std::uint64_t FallbackFrames = 0;
    inline std::uint64_t DirectCandidateRejected = 0;
    inline std::uint64_t ConsumerFenceSuccess = 0;
    inline std::uint64_t ConsumerFenceTimeout = 0;
    inline std::uint64_t StaleFallbackInvalidations = 0;
    inline bool FirstDirectPassLogged = false;
    inline bool FirstDirectRejectLogged = false;
    inline bool FirstGpuSafeAckLogged = false;

    inline HANDLE PoseMapping = nullptr;
    inline OutRunVR::SharedPoseState* PoseState = nullptr;
    inline ID3D11Query* ConsumerFence = nullptr;

    inline std::uint64_t LastObservedCaptureFresh = 0;
    inline ULONGLONG LastCaptureFreshMs = 0;

    struct DirectHostState
    {
        bool valid = false;
        std::uint32_t flags = 0;
        std::uint32_t hostPid = 0;
        std::uint32_t openedFrame = 0;
        std::uint32_t gpuCompletedFrame = 0;
    };

    inline bool EnsurePoseState() noexcept
    {
        if (PoseState &&
            PoseState->magic == OutRunVR::SharedMagic &&
            PoseState->protocolVersion == OutRunVR::SharedProtocolVersion &&
            PoseState->structSize == sizeof(OutRunVR::SharedPoseState))
            return true;

        if (PoseState)
        {
            UnmapViewOfFile(PoseState);
            PoseState = nullptr;
        }
        if (PoseMapping)
        {
            CloseHandle(PoseMapping);
            PoseMapping = nullptr;
        }

        PoseMapping = OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, OutRunVR::SharedMemoryName);
        if (!PoseMapping)
            return false;

        PoseState = static_cast<OutRunVR::SharedPoseState*>(MapViewOfFile(
            PoseMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedPoseState)));
        if (!PoseState)
        {
            CloseHandle(PoseMapping);
            PoseMapping = nullptr;
            return false;
        }

        if (PoseState->magic != OutRunVR::SharedMagic ||
            PoseState->protocolVersion != OutRunVR::SharedProtocolVersion ||
            PoseState->structSize != sizeof(OutRunVR::SharedPoseState))
        {
            UnmapViewOfFile(PoseState);
            PoseState = nullptr;
            CloseHandle(PoseMapping);
            PoseMapping = nullptr;
            return false;
        }
        return true;
    }

    inline DirectHostState ReadDirectHostState() noexcept
    {
        DirectHostState out{};
        if (!EnsurePoseState())
            return out;

        for (int attempt = 0; attempt < 4; ++attempt)
        {
            const std::uint32_t before = PoseState->sequence;
            if (before & 1u)
                continue;
            MemoryBarrier();
            out.flags = PoseState->flags;
            out.hostPid = PoseState->hostPid;
            MemoryBarrier();
            const std::uint32_t after = PoseState->sequence;
            if (before != after || (after & 1u))
                continue;

            out.openedFrame = static_cast<std::uint32_t>(InterlockedCompareExchange(
                reinterpret_cast<volatile LONG*>(&PoseState->hostDirectConsumedFrameId), 0, 0));
            out.gpuCompletedFrame = static_cast<std::uint32_t>(InterlockedCompareExchange(
                reinterpret_cast<volatile LONG*>(&PoseState->reserved[OutRunVRR13::HostDirectGpuCompletedFrameIndex]),
                0, 0));
            constexpr std::uint32_t required =
                OutRunVR::HostAlive |
                OutRunVR::HostDirectGpuTransport |
                OutRunVR::HostDirectGpuReady;
            out.valid = out.hostPid != 0 && (out.flags & required) == required;
            return out;
        }
        return {};
    }

    inline bool IncomingProjectionValid(const XrFrameEndInfo* endInfo) noexcept
    {
        return endInfo && endInfo->layerCount > 0 && endInfo->layers &&
            endInfo->layers[0] && endInfo->layers[0]->type == XR_TYPE_COMPOSITION_LAYER_PROJECTION;
    }

    inline bool EnsureConsumerFence() noexcept
    {
        if (ConsumerFence)
            return true;
        if (!OutRunVrFinalTest::Device)
            return false;
        D3D11_QUERY_DESC desc{};
        desc.Query = D3D11_QUERY_EVENT;
        return SUCCEEDED(OutRunVrFinalTest::Device->CreateQuery(&desc, &ConsumerFence)) && ConsumerFence;
    }

    inline bool MarkGpuConsumptionComplete(std::uint32_t frameId) noexcept
    {
        if (!frameId || !PoseState || !OutRunVrFinalTest::Context || !EnsureConsumerFence())
            return false;

        // RenderProjection has already queued all SRV sampling before main.cpp
        // reaches xrEndFrame.  An EVENT query inserted here retires only after
        // those commands have completed on the D3D11 GPU timeline.
        OutRunVrFinalTest::Context->End(ConsumerFence);
        OutRunVrFinalTest::Context->Flush();
        const ULONGLONG start = GetTickCount64();
        for (;;)
        {
            const HRESULT hr = OutRunVrFinalTest::Context->GetData(
                ConsumerFence, nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
            if (hr == S_OK)
                break;
            if (FAILED(hr) || GetTickCount64() - start >= ConsumerFenceTimeoutMs)
            {
                ++ConsumerFenceTimeout;
                return false;
            }
            SwitchToThread();
        }

        InterlockedExchange(
            reinterpret_cast<volatile LONG*>(&PoseState->reserved[OutRunVRR13::HostDirectGpuCompletedFrameIndex]),
            static_cast<LONG>(frameId));
        ++ConsumerFenceSuccess;
        if (!FirstGpuSafeAckLogged)
        {
            FirstGpuSafeAckLogged = true;
            std::cerr << "[D3D9Ex R13] GPU-consumer completion ACK active frame=" << frameId
                      << "; producer ring reuse now waits for D3D11 completion\n";
        }
        return true;
    }

    inline void ObserveCaptureFreshness() noexcept
    {
        using namespace OutRunVrSbsCaptureOverride;
        if (CaptureFresh != LastObservedCaptureFresh)
        {
            LastObservedCaptureFresh = CaptureFresh;
            LastCaptureFreshMs = GetTickCount64();
        }
    }

    inline void InvalidateStaleFallbackSource() noexcept
    {
        using namespace OutRunVrSbsCaptureOverride;
        ObserveCaptureFreshness();
        if (HaveSource && LastCaptureFreshMs != 0 &&
            GetTickCount64() - LastCaptureFreshMs > FallbackSourceMaxAgeMs)
        {
            HaveSource = false;
            ++StaleFallbackInvalidations;
            std::cerr << "[R13] stale Desktop Duplication source invalidated after "
                      << FallbackSourceMaxAgeMs << "ms without a fresh capture\n";
        }
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session, const XrFrameEndInfo* endInfo)
    {
        // The incoming projection itself is the authoritative evidence that the
        // legacy host matched a game frame and RenderProjection sampled its
        // direct SRVs.  Do not re-read LatestFrame here for arbitration: doing
        // so raced frame N's incoming projection against a newly published N+1.
        const DirectHostState state = ReadDirectHostState();
        const bool directCandidate = IncomingProjectionValid(endInfo) && state.valid && state.openedFrame != 0;

        if (directCandidate && MarkGpuConsumptionComplete(state.openedFrame))
        {
            ++DirectPassFrames;
            if (!FirstDirectPassLogged)
            {
                FirstDirectPassLogged = true;
                std::cerr
                    << "[D3D9Ex] ZERO-COPY projection passthrough ACTIVE build=" << BuildId
                    << " frame=" << state.openedFrame
                    << "; exact opened-frame ACK + GPU completion matched; R10 Desktop Duplication bypassed\n";
            }
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }

        if (directCandidate)
        {
            ++DirectCandidateRejected;
            if (!FirstDirectRejectLogged)
            {
                FirstDirectRejectLogged = true;
                std::cerr
                    << "[D3D9Ex R13] direct projection exists but GPU-consumer completion was not proven; keeping R10 fallback\n";
            }
        }

        ++FallbackFrames;
        InvalidateStaleFallbackSource();
        const XrResult result = OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);
        ObserveCaptureFreshness();
        return result;
    }
}

#define xrEndFrame OutRunVrD3D9ExDirectPassthrough::EndFrame
