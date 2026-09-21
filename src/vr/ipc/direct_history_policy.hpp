#pragma once

#include "vr/ipc/protocol.hpp"

namespace OutRunVR::DirectHistoryPolicy
{
    inline std::uint32_t StereoIntentEpoch(
        const SharedRenderFrameState& frame) noexcept
    {
        return frame.reserved[RenderFrameStereoIntentEpochIndex];
    }

    inline bool LatestPublicationAllowsHistory(
        const SharedRenderFrameState& latest) noexcept
    {
        constexpr std::uint32_t required =
            RenderFrameDirectGpuTransport |
            RenderFrameStereoComplete |
            RenderFrameWorldStereo |
            RenderFrameDrawDuplicated |
            RenderFrameEffectivePoseValid;

        return StereoIntentEpoch(latest) != 0 &&
            latest.frameId != 0 &&
            latest.state == StereoSbsActive &&
            (latest.flags & RenderFramePresentInFlight) == 0 &&
            (latest.flags & required) == required;
    }

    inline bool SameStereoIntentEpoch(
        const SharedRenderFrameState& frame,
        const SharedRenderFrameState& latest) noexcept
    {
        const std::uint32_t epoch = StereoIntentEpoch(latest);
        return epoch != 0 && StereoIntentEpoch(frame) == epoch;
    }
}
