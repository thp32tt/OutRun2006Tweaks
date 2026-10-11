#include "../src/runtime/cadence_schedule.hpp"
#include <cstdint>
#include <iostream>
#include <limits>

#define REQUIRE(x) do { if (!(x)) { std::cerr << "cadence schedule failure at " << __LINE__ << ": " << #x << "\n"; return 1; } } while (false)

int main()
{
    using OutRunVR::CadenceSchedule::Advance;
    // Nominal 90-Hz XR / 60-Hz game phase: never renew the deadline on early ticks.
    const std::int64_t period = 16'666'667;
    auto first = Advance(10'000'000'000, period, 0);
    REQUIRE(first.issue && first.nextDisplayTime == 10'016'666'667);
    auto early = Advance(10'011'111'111, period, first.nextDisplayTime);
    REQUIRE(!early.issue && early.nextDisplayTime == first.nextDisplayTime);
    auto due = Advance(10'022'222'222, period, early.nextDisplayTime);
    REQUIRE(due.issue && due.nextDisplayTime == 10'033'333'334);

    // A 12-hour compositor pause must be constant-time, not ~2.6M loop steps.
    const auto leap = Advance(43'210'000'000'000, period, due.nextDisplayTime);
    REQUIRE(leap.issue && leap.nextDisplayTime > 43'210'000'000'000);
    REQUIRE(leap.nextDisplayTime - 43'210'000'000'000 <= period);

    // A new OpenXR time epoch after reconnect must issue immediately.
    const auto restart = Advance(4'000'000'000, period, leap.nextDisplayTime);
    REQUIRE(restart.issue && restart.nextDisplayTime == 4'016'666'667);
    // Do not mistake normal early arrival (including normal jitter) for restart.
    const auto jitter = Advance(4'010'000'000, period, restart.nextDisplayTime);
    REQUIRE(!jitter.issue && jitter.nextDisplayTime == restart.nextDisplayTime);

    // Invalid timing observations never publish a spurious cadence request.
    REQUIRE(!Advance(0, period, 42).issue);
    REQUIRE(!Advance(1, 0, 42).issue);
    REQUIRE(!Advance(-1, period, 42).issue);

    // Large positive XrTime must not overflow multiplication/addition.
    constexpr auto max = std::numeric_limits<std::int64_t>::max();
    const auto end = Advance(max - 10, period, max - 100);
    REQUIRE(end.issue && end.nextDisplayTime == max);
    // A gap exactly at the backward reset threshold keeps the old phase.
    REQUIRE(!Advance(100, period, 100 + 1'000'000'000).issue);

    std::cout << "CADENCE-SCHEDULE PASS: 90/60 phase, pause, XR epoch reset, overflow\n";
    return 0;
}
