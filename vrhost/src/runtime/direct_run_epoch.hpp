#pragma once
#include <cstdint>

// Frame IDs are monotonic only within one DirectGPU game run. The host can
// outlive a restarted game, so its prior last-displayed cursor must not gate
// frame IDs published under a new runGeneration/PID. The reader independently
// rejects invalid/stale run publications before this cursor observes them.
namespace OutRunVrDirectRunEpoch
{
    struct Identity
    {
        std::uint32_t runGeneration = 0;
        std::uint32_t gamePid = 0;
    };

    struct Cursor
    {
        Identity active{};

        constexpr bool Observe(const Identity& incoming) noexcept
        {
            // Invalid/transitional publications cannot change a valid epoch.
            if (!incoming.runGeneration || !incoming.gamePid)
                return false;
            const bool changed = active.runGeneration != 0 &&
                (active.runGeneration != incoming.runGeneration ||
                 active.gamePid != incoming.gamePid);
            active = incoming;
            return changed;
        }
    };
}
