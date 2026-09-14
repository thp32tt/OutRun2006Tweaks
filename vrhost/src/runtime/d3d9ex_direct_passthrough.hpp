#pragma once

// Final arbitration layer between the R10 Desktop-Duplication fallback and the
// already-existing D3D9Ex -> D3D11 shared-eye ring.
//
// R10 remains the default image source for classic D3D9 and for menus. When the
// game publishes a complete Frame.v2 carrying RenderFrameDirectGpuTransport,
// the legacy host has opened the shared L/R textures, and that exact frameId has
// been ACKed through Pose.v2, do not replace the direct projection layer with a
// second desktop capture.
//
// This keeps one binary usable for both paths:
//   classic D3D9  -> R10 SBS/Desktop Duplication fallback
//   D3D9Ex direct -> shared L/R textures -> legacy host projection (zero-copy)

#include "sbs_capture_override.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif

#include <cstdint>
#include <iostream>

namespace OutRunVrD3D9ExDirectPassthrough
{
    inline constexpr const char* BuildId = "D3D9Ex-direct-passthrough-20260915";
    inline std::uint64_t DirectPassFrames = 0;
    inline std::uint64_t FallbackFrames = 0;
    inline std::uint64_t DirectCandidateRejected = 0;
    inline bool FirstDirectPassLogged = false;
    inline bool FirstDirectRejectLogged = false;

    inline HANDLE PoseMapping = nullptr;
    inline const OutRunVR::SharedPoseState* PoseState = nullptr;

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

        PoseMapping = OpenFileMappingW(FILE_MAP_READ, FALSE, OutRunVR::SharedMemoryName);
        if (!PoseMapping)
            return false;

        PoseState = static_cast<const OutRunVR::SharedPoseState*>(MapViewOfFile(
            PoseMapping, FILE_MAP_READ, 0, 0, sizeof(OutRunVR::SharedPoseState)));
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

    inline bool HostAckedDirectFrame(std::uint32_t frameId) noexcept
    {
        if (!frameId || !EnsurePoseState())
            return false;

        for (int attempt = 0; attempt < 4; ++attempt)
        {
            const std::uint32_t before = PoseState->sequence;
            if (before & 1u)
                continue;
            MemoryBarrier();
            const std::uint32_t flags = PoseState->flags;
            const std::uint32_t hostPid = PoseState->hostPid;
            MemoryBarrier();
            const std::uint32_t after = PoseState->sequence;
            if (before != after || (after & 1u))
                continue;

            constexpr std::uint32_t required =
                OutRunVR::HostAlive |
                OutRunVR::HostDirectGpuTransport |
                OutRunVR::HostDirectGpuReady;
            if (!hostPid || (flags & required) != required)
                return false;

            // AckDirectFrame uses InterlockedExchange outside the pose seqlock.
            // Read it atomically and require the exact frame being considered at
            // this xrEndFrame boundary; a previous frame is not sufficient.
            const std::uint32_t consumed = static_cast<std::uint32_t>(
                InterlockedCompareExchange(
                    reinterpret_cast<volatile LONG*>(
                        const_cast<volatile std::uint32_t*>(&PoseState->hostDirectConsumedFrameId)),
                    0, 0));
            return consumed == frameId;
        }
        return false;
    }

    inline bool IncomingProjectionValid(const XrFrameEndInfo* endInfo) noexcept
    {
        return endInfo && endInfo->layerCount > 0 && endInfo->layers &&
            endInfo->layers[0] && endInfo->layers[0]->type == XR_TYPE_COMPOSITION_LAYER_PROJECTION;
    }

    inline bool DirectFrameCandidate(const XrFrameEndInfo* endInfo) noexcept
    {
        using namespace OutRunVrSbsCaptureOverride;
        if (!IncomingProjectionValid(endInfo) || !LastStereoFrameValid)
            return false;
        if (GetTickCount64() - LastStereoFrameMs > 500)
            return false;
        constexpr std::uint32_t complete =
            OutRunVR::RenderFrameStereoComplete |
            OutRunVR::RenderFrameWorldStereo |
            OutRunVR::RenderFrameDrawDuplicated |
            OutRunVR::RenderFrameEffectivePoseValid |
            OutRunVR::RenderFrameDirectGpuTransport;
        return LastStereoFrame.state == OutRunVR::StereoSbsActive &&
            LastStereoFrame.frameId != 0 && LastStereoFrame.sourcePoseSequence != 0 &&
            (LastStereoFrame.flags & OutRunVR::RenderFramePresentInFlight) == 0 &&
            (LastStereoFrame.flags & complete) == complete;
    }

    inline bool DirectFrameReady(const XrFrameEndInfo* endInfo) noexcept
    {
        if (!DirectFrameCandidate(endInfo))
            return false;
        return HostAckedDirectFrame(OutRunVrSbsCaptureOverride::LastStereoFrame.frameId);
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session, const XrFrameEndInfo* endInfo)
    {
        // Refresh the same stable Frame.v2 cache used by R10 before deciding.
        OutRunVrSbsCaptureOverride::UpdateStereoFrameCache();
        const bool candidate = DirectFrameCandidate(endInfo);
        if (candidate && DirectFrameReady(endInfo))
        {
            ++DirectPassFrames;
            if (!FirstDirectPassLogged)
            {
                FirstDirectPassLogged = true;
                std::cerr
                    << "[D3D9Ex] ZERO-COPY projection passthrough ACTIVE build=" << BuildId
                    << " frame=" << OutRunVrSbsCaptureOverride::LastStereoFrame.frameId
                    << "; exact host shared-eye ACK matched; R10 Desktop Duplication bypassed for direct gameplay frames\n";
            }
            // OutRunVrFinalTest is the layer immediately below R10. Calling it
            // directly preserves the projection layer produced from the opened
            // D3D9Ex shared eye textures and avoids another desktop capture.
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }

        if (candidate)
        {
            ++DirectCandidateRejected;
            if (!FirstDirectRejectLogged)
            {
                FirstDirectRejectLogged = true;
                std::cerr
                    << "[D3D9Ex] direct frame published but exact host shared-eye ACK is not ready; keeping R10 Desktop Duplication fallback\n";
            }
        }

        ++FallbackFrames;
        return OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);
    }
}

#define xrEndFrame OutRunVrD3D9ExDirectPassthrough::EndFrame
