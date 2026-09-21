#pragma once

#include "vr/ipc/protocol.hpp"

namespace OutRunVR::DirectHistoryPolicy
{
    inline bool LatestPublicationBlocksHistory(
        const SharedRenderFrameState& latest) noexcept
    {
        return latest.frameId == 0 &&
            latest.state == StereoDisabled &&
            (latest.flags & RenderFramePresentInFlight) == 0;
    }
}
