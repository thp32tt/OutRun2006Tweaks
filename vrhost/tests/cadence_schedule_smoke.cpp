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

    // Regression: XR STOPPING/READY may restart its display-time epoch near
    // the old deadline (<1s), or return at a different headset refresh rate.
    // Keeping the previous schedule incorrectly suppresses first game renders.
    OutRunVR::CadenceSchedule::SessionEpoch epoch{};
    epoch.nextRequestDisplayTime = due.nextDisplayTime;
    epoch.activeRenderHz = 90.0f;
    epoch.pendingRenderHz = 72.0f;
    epoch.pendingRenderHzSamples = 19;
    epoch.actualXrHz = 89.9;
    epoch.actualDisplayPeriodMs = 11.1;
    epoch.lastLoggedXrHz = 90.0;
    REQUIRE(!epoch.OnRunningTransition(true, true));
    REQUIRE(epoch.nextRequestDisplayTime == due.nextDisplayTime &&
        epoch.pendingRenderHzSamples == 19);
    const auto staleResume = Advance(10'018'000'000, period,
        epoch.nextRequestDisplayTime);
    REQUIRE(!staleResume.issue); // pre-fix: suppresses first frame
    REQUIRE(epoch.OnRunningTransition(true, false));
    REQUIRE(epoch.nextRequestDisplayTime == 0 &&
        epoch.activeRenderHz == 0.0f &&
        epoch.pendingRenderHz == 0.0f &&
        epoch.pendingRenderHzSamples == 0 &&
        epoch.actualXrHz == 0.0 &&
        epoch.actualDisplayPeriodMs == 0.0 &&
        epoch.lastLoggedXrHz == 0.0);
    // 15ms backwards is below the old 1s discontinuity threshold, yet the
    // resumed first frame must be due rather than waiting for the old phase.
    const auto resumed = Advance(10'018'000'000, period,
        epoch.nextRequestDisplayTime);
    REQUIRE(resumed.issue && resumed.nextDisplayTime == 10'034'666'667);
    epoch.nextRequestDisplayTime = resumed.nextDisplayTime;
    REQUIRE(!epoch.OnRunningTransition(false, false));
    REQUIRE(epoch.nextRequestDisplayTime == resumed.nextDisplayTime);
    REQUIRE(epoch.OnRunningTransition(false, true));
    REQUIRE(epoch.nextRequestDisplayTime == 0);
    // Fresh refresh sampling may select a new 72Hz mode, not inherit 90Hz.
    REQUIRE(epoch.activeRenderHz == 0.0f && epoch.actualXrHz == 0.0);

    std::cout << "CADENCE-SCHEDULE PASS: 90/60 phase, pause, XR epoch reset, overflow\n";
    return 0;
}
