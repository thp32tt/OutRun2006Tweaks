#pragma once

// Final arbitration layer between the R10 Desktop-Duplication fallback and the
// already-existing D3D9Ex -> D3D11 shared-eye ring.
//
// R10 remains the default image source for classic D3D9 and for menus. When the
// game publishes a complete Frame.v2 carrying RenderFrameDirectGpuTransport and
// the legacy host has already produced a valid projection layer from the shared
// L/R textures, do not replace that layer with a second desktop capture.
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
    inline bool FirstDirectPassLogged = false;

    inline bool IncomingProjectionValid(const XrFrameEndInfo* endInfo) noexcept
    {
        return endInfo && endInfo->layerCount > 0 && endInfo->layers &&
            endInfo->layers[0] && endInfo->layers[0]->type == XR_TYPE_COMPOSITION_LAYER_PROJECTION;
    }

    inline bool DirectFrameReady(const XrFrameEndInfo* endInfo) noexcept
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

    inline XrResult XRAPI_CALL EndFrame(XrSession session, const XrFrameEndInfo* endInfo)
    {
        // Refresh the same stable Frame.v2 cache used by R10 before deciding.
        OutRunVrSbsCaptureOverride::UpdateStereoFrameCache();
        if (DirectFrameReady(endInfo))
        {
            ++DirectPassFrames;
            if (!FirstDirectPassLogged)
            {
                FirstDirectPassLogged = true;
                std::cerr
                    << "[D3D9Ex] ZERO-COPY projection passthrough ACTIVE build=" << BuildId
                    << " frame=" << OutRunVrSbsCaptureOverride::LastStereoFrame.frameId
                    << "; R10 Desktop Duplication override bypassed for direct gameplay frames\n";
            }
            // OutRunVrFinalTest is the layer immediately below R10. Calling it
            // directly preserves the projection layer produced from the opened
            // D3D9Ex shared eye textures and avoids another desktop capture.
            return OutRunVrFinalTest::EndFrame(session, endInfo);
        }

        ++FallbackFrames;
        return OutRunVrSbsCaptureOverride::EndFrame(session, endInfo);
    }
}

#define xrEndFrame OutRunVrD3D9ExDirectPassthrough::EndFrame
