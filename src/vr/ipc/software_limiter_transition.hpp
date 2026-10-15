#pragma once

// Keep software frame-pacing deadlines tied to the clock which owns Present.
// xrWaitFrame, unlimited load-screen rendering, and zero-limit desktop frames
// must not leave a stale software deadline to be used on re-entry.
namespace OutRunVR::FramePacing
{
    struct SoftwareLimiterTransition
    {
        bool active = false;
        int hz = 0;

        constexpr bool Observe(bool shouldLimit, int requestedHz) noexcept
        {
            const bool next = shouldLimit && requestedHz > 0;
            const bool rebase = next && (!active || hz != requestedHz);
            active = next;
            hz = next ? requestedHz : 0;
            return rebase;
        }
    };

    constexpr bool SoftwareLimiterTransitionRegression() noexcept
    {
        SoftwareLimiterTransition state{};
        // Initial fallback must base itself on the current QPC, not on
        // the construction-time timestamp.
        if (!state.Observe(true, 60) || state.Observe(true, 60))
            return false;
        // xrWaitFrame has exclusive cadence ownership for arbitrarily long.
        if (state.Observe(false, 0) || state.Observe(false, 0))
            return false;
        if (!state.Observe(true, 60) || state.Observe(true, 60))
            return false;
        // A runtime cap change must not spend an old 60-Hz deadline at 90 Hz.
        if (!state.Observe(true, 90) || state.Observe(true, 90))
            return false;
        // Fast-load unlimited and ordinary desktop/unlimited use the same
        // safe exit/re-entry rule; only the first limiting frame rebases.
        if (state.Observe(false, 90) || !state.Observe(true, 90))
            return false;
        return state.active && state.hz == 90;
    }
    static_assert(SoftwareLimiterTransitionRegression(),
        "XR/cap/load transitions must rebase exactly once, not every frame");
}
