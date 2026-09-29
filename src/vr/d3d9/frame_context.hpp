#pragma once

#include <cstdint>

namespace OutRunVR::FrameState
{
    struct FrameContext
    {
        bool stageIdentitySeen = false;
        int lastStageIdentity = -1;
        std::uint64_t stageTransitionHolds = 0;
        int stageHoldRemaining = 0;

        void ResetStageTransition() noexcept
        {
            stageIdentitySeen = false;
            lastStageIdentity = -1;
            stageHoldRemaining = 0;
        }
    };
}
