#pragma once

namespace OutRunVR::Lifecycle
{
    constexpr bool ResetReplayHealthy(
        bool resetSucceeded, bool replaySucceeded) noexcept
    {
        return resetSucceeded && replaySucceeded;
    }

    static_assert(ResetReplayHealthy(true, true));
    static_assert(!ResetReplayHealthy(false, true));
    static_assert(!ResetReplayHealthy(true, false));
    static_assert(!ResetReplayHealthy(false, false));
}
