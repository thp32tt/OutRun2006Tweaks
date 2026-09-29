#pragma once

#include "vr/ipc/protocol.hpp"

#include <cstdint>

namespace OutRunVR::FrameContract
{
    inline constexpr std::uint32_t GameplayStereoRequiredFlags =
        RenderFrameStereoComplete |
        RenderFrameWorldStereo |
        RenderFrameDrawDuplicated |
        RenderFrameEffectivePoseValid;

    inline bool HasValidDirectGpuMetadata(
        const SharedRenderFrameState& frame) noexcept
    {
        if ((frame.flags & RenderFrameDirectGpuTransport) == 0)
            return true;

        const std::uint32_t slot =
            frame.reserved[RenderFrameDirectSlotIndex];
        const std::uint32_t generation =
            frame.reserved[RenderFrameDirectGenerationIndex];
        const std::uint32_t width =
            frame.reserved[RenderFrameDirectWidthIndex];
        const std::uint32_t height =
            frame.reserved[RenderFrameDirectHeightIndex];
        const std::uint32_t leftHandle =
            frame.reserved[RenderFrameDirectLeftHandleIndex];
        const std::uint32_t rightHandle =
            frame.reserved[RenderFrameDirectRightHandleIndex];

        return slot < RenderFrameRingSize &&
            generation != 0 &&
            leftHandle != 0 &&
            rightHandle != 0 &&
            width != 0 &&
            height != 0 &&
            width == frame.backbufferWidth &&
            height == frame.backbufferHeight;
    }

    inline bool IsUsableGameplayStereoFrame(
        const SharedRenderFrameState& frame) noexcept
    {
        return frame.frameId != 0 &&
            frame.sourcePoseSequence != 0 &&
            frame.presentationMode == PresentationGameplay &&
            frame.state == StereoSbsActive &&
            frame.failureReason == StereoFailureNone &&
            frame.presentQpc > 0 &&
            frame.backbufferWidth != 0 &&
            frame.backbufferHeight != 0 &&
            (frame.flags & RenderFramePresentInFlight) == 0 &&
            (frame.flags & GameplayStereoRequiredFlags) ==
                GameplayStereoRequiredFlags &&
            HasValidDirectGpuMetadata(frame);
    }
}
