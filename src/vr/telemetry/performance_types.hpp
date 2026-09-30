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
    struct PerfWindow
    {
        std::uint64_t frames = 0;
        std::uint64_t spikes = 0;
        std::uint64_t frameUsTotal = 0;
        std::uint64_t maxFrameUs = 0;
        std::uint64_t presentUsTotal = 0;
        std::uint64_t maxPresentUs = 0;
        std::uint64_t drawsTotal = 0;
        std::uint64_t maxDraws = 0;
        std::uint64_t primitivesTotal = 0;
        std::uint64_t maxPrimitives = 0;
        std::uint64_t maxTriangles = 0;
        std::uint64_t maxUpDraws = 0;
        std::uint64_t maxAlphaBlendDraws = 0;
        std::uint64_t maxParticleLikeDraws = 0;
        std::uint64_t maxParticleLikePrimitives = 0;
    };
}
