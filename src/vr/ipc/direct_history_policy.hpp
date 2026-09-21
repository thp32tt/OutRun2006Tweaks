#pragma once

#include "vr/ipc/protocol.hpp"

namespace OutRunVR::DirectHistoryPolicy
{
    inline std::uint32_t StereoIntentEpoch(
        const SharedRenderFrameState& frame) noexcept
    {
        return frame.reserved[RenderFrameStereoIntentEpochIndex];
    }

    inline bool LatestPublicationDefinesHistoryEpoch(
        const SharedRenderFrameState& latest) noexcept
    {
        return StereoIntentEpoch(latest) != 0;
    }

    inline bool SameStereoIntentEpoch(
        const SharedRenderFrameState& frame,
        const SharedRenderFrameState& latest) noexcept
    {
        const std::uint32_t epoch = StereoIntentEpoch(latest);
        return epoch != 0 && StereoIntentEpoch(frame) == epoch;
    }
}
