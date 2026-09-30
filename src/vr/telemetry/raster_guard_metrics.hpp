#pragma once

#include <cstdint>

namespace OutRunVR::Telemetry
{
    struct RasterGuardMetrics
    {
        std::uint64_t draws = 0;
        bool firstLogged = false;

        void NoteDraw() noexcept { ++draws; }

        bool MarkFirstLogged() noexcept
        {
            if (firstLogged)
                return false;
            firstLogged = true;
            return true;
        }
    };
}
