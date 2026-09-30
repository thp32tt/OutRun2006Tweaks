#pragma once

#include <cstdint>

namespace OutRunVR::Telemetry
{
    struct RasterGuardMetrics
    {
        std::uint64_t draws = 0;
        bool firstLogged = false;
    };
}
