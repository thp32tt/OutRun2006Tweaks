#include "../src/runtime/cadence_presented_wait.hpp"

#include <cstdint>
#include <iostream>

int main()
{
    using OutRunVR::CadenceWait::AwaitPresented;

    // A stale auto-reset event must not count as this request's presentation.
    std::uint64_t now = 100;
    std::uint32_t presented = 41;
    int waits = 0;
    const bool matched = AwaitPresented(12,
        [&] { return presented == 42; },
        [&](std::uint32_t remaining) {
            ++waits;
            if (waits == 1) {
                if (remaining != 12) return false;
                now += 3; // stale completion for request 41
            } else {
                if (remaining != 9) return false;
                now += 2;
                presented = 42;
            }
            return true;
        },
        [&] { return now; });
    if (!matched || waits != 2 || now != 105) return 1;

    // Multiple stale events consume the same finite budget, not fresh time.
    now = 200;
    waits = 0;
    const bool timedOut = AwaitPresented(7,
        [] { return false; },
        [&](std::uint32_t remaining) {
            ++waits;
            if (remaining != (waits == 1 ? 7u : 3u)) return false;
            now += 4;
            return true;
        },
        [&] { return now; });
    if (timedOut || waits != 2 || now != 208) return 2;

    // A finished request is accepted without blocking or consuming an event.
    waits = 0;
    if (!AwaitPresented(5, [] { return true; },
            [&](std::uint32_t) { ++waits; return false; },
            [&] { return now; }) || waits != 0) return 3;

    // Timeout or failed wait reads the client once more to close the race.
    int reads = 0;
    now = 300;
    const bool boundaryMatch = AwaitPresented(8,
        [&] { return ++reads == 2; },
        [&](std::uint32_t) { now += 8; return false; },
        [&] { return now; });
    if (!boundaryMatch || reads != 2) return 4;

    std::cout << "cadence-presented-wait PASS: stale/timeout/already-ready/boundary\n";
    return 0;
}
