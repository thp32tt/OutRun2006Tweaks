#pragma once

#include <cstdint>

namespace OutRunVR::Telemetry
{
    struct FrameWorkload
    {
        std::uint64_t draws = 0;
        std::uint64_t primitives = 0;
        std::uint64_t triangles = 0;
        std::uint64_t pointLinePrimitives = 0;
        std::uint64_t indexedDraws = 0;
        std::uint64_t upDraws = 0;
        std::uint64_t alphaBlendDraws = 0;
        std::uint64_t alphaBlendPrimitives = 0;
        std::uint64_t alphaTestDraws = 0;
        std::uint64_t particleLikeDraws = 0;
        std::uint64_t particleLikePrimitives = 0;
        std::uint64_t effectUnknownDraws = 0;
        std::uint64_t fenceWaitUs = 0;
        std::uint64_t fencePolls = 0;
    };
}
