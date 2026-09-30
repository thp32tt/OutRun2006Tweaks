#pragma once

#include <Windows.h>
#include <cstdint>

namespace OutRunVR::Telemetry
{
    struct DepthStencilMetrics
    {
        ULONGLONG lastLogMs = 0;
        std::uint64_t syncs = 0;
        std::uint64_t hits = 0;
        std::uint64_t live = 0;
        std::uint64_t readFail = 0;
        std::uint64_t resetOk = 0;
        std::uint64_t resetFail = 0;
    };
}
