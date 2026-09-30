#pragma once

#include <Windows.h>
#include <cstdint>

namespace OutRunVR::Telemetry
{
    struct StereoFrameCounters
    {
        std::uint64_t epoch = 0;
        std::uint64_t draws = 0;
        std::uint64_t main = 0;
        std::uint64_t offscreen = 0;
        std::uint64_t aux = 0;
        std::uint64_t fastWorld = 0;
        std::uint64_t hud = 0;
        std::uint64_t fragile = 0;
        std::uint64_t unstable = 0;
        std::uint64_t fallback = 0;
    };
    struct StereoWindowCounters
    {
        std::uint64_t presents = 0;
        std::uint64_t draws = 0;
        std::uint64_t main = 0;
        std::uint64_t offscreen = 0;
        std::uint64_t aux = 0;
        std::uint64_t fastWorld = 0;
        std::uint64_t hud = 0;
        std::uint64_t fragile = 0;
        std::uint64_t unstable = 0;
        std::uint64_t fallback = 0;
        std::uint64_t maxDraws = 0;
        ULONGLONG lastLogMs = 0;
    };
}
