#pragma once

#include <cstdint>

namespace OutRunVR::CadenceWait
{
    // Auto-reset events carry no request identity: a late completion from the
    // previous frame may wake us while the new request is still outstanding.
    // Always re-read the shared, sequence-validated request ID after a wake,
    // and use one absolute deadline rather than renewing the frame budget.
    template <typename MatchesRequest, typename WaitEvent, typename ClockMs>
    bool AwaitPresented(std::uint32_t budgetMs, MatchesRequest&& matches,
        WaitEvent&& waitEvent, ClockMs&& clockMs) noexcept
    {
        const std::uint64_t start = clockMs();
        const std::uint64_t deadline = start + budgetMs;
        for (;;)
        {
            if (matches())
                return true;
            const std::uint64_t now = clockMs();
            if (now >= deadline)
            {
                // The producer can publish this exact request between the
                // preceding shared-state read and the deadline clock read.
                // A final sequence-validated read avoids dropping an already
                // completed game frame without extending the XR budget.
                return matches();
            }
            const auto remaining = static_cast<std::uint32_t>(deadline - now);
            // WAIT_TIMEOUT or WAIT_FAILED must not spin. A last shared-state
            // read still accepts a publication racing the wait boundary.
            if (!waitEvent(remaining))
                return matches();
        }
    }
}
