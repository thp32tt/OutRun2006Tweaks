#pragma once

#include <d3d9.h>

namespace OutRunVR::Lifecycle
{
    constexpr bool ResetReplayHealthy(
        bool resetSucceeded, bool replaySucceeded) noexcept
    {
        return resetSucceeded && replaySucceeded;
    }

    constexpr bool DeviceNeedsResetBypass(HRESULT cooperative) noexcept
    {
        return cooperative == D3DERR_DEVICELOST ||
            cooperative == D3DERR_DEVICENOTRESET;
    }

    static_assert(ResetReplayHealthy(true, true));
    static_assert(!ResetReplayHealthy(false, true));
    static_assert(!ResetReplayHealthy(true, false));
    static_assert(!ResetReplayHealthy(false, false));
}
