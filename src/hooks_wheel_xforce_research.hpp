#pragma once

#include <cmath>
#include <cstddef>

#include "plugin.hpp"
#include "game_addrs.hpp"

// Research-only capture for the two unknown floats adjacent to
// EVWORK_CAR::actionforce_DBC. These values are intentionally never consumed by
// the force model. Their only purpose is to produce a timestamped input-side
// stream that can be aligned with the physics-side XFORCE60 telemetry and
// inspected offline before any native field is trusted as tyre/rack force.
namespace Settings
{
    extern Setting<bool> WheelFFBXForceCapture60Hz; // hooks_wheel_ffb.cpp
}

static_assert(offsetof(EVWORK_CAR, field_DC0) == 0xDC0,
    "EVWORK_CAR::field_DC0 offset drifted; X-Force neighbor capture would read the wrong memory");
static_assert(offsetof(EVWORK_CAR, field_DC4) == 0xDC4,
    "EVWORK_CAR::field_DC4 offset drifted; X-Force neighbor capture would read the wrong memory");

namespace WheelXForceResearch
{
    inline DWORD lastLogTick = 0;
    inline bool baselineValid = false;
    inline float prevDbc = 0.0f;
    inline float prevDc0 = 0.0f;
    inline float prevDc4 = 0.0f;

    inline void reset()
    {
        lastLogTick = 0;
        baselineValid = false;
        prevDbc = 0.0f;
        prevDc0 = 0.0f;
        prevDc4 = 0.0f;
    }

    inline void capture_neighbors()
    {
        if (!Settings::WheelFFBXForceCapture60Hz ||
            !Game::current_mode || *Game::current_mode != STATE_GAME)
        {
            reset();
            return;
        }

        EVWORK_CAR* car = Game::pl_car();
        if (!car)
        {
            reset();
            return;
        }

        const DWORD now = GetTickCount();
        // Input update can run faster than the fixed 60 Hz physics loop. Bound
        // this auxiliary stream to approximately the same cadence so an opt-in
        // capture does not scale its log volume with render refresh rate.
        if (lastLogTick != 0 && static_cast<DWORD>(now - lastLogTick) < 15u)
            return;

        const float dbc = car->actionforce_DBC;
        const float dc0 = car->field_DC0;
        const float dc4 = car->field_DC4;
        const bool finite =
            std::isfinite(dbc) && std::isfinite(dc0) && std::isfinite(dc4);

        const float dDbc = finite && baselineValid ? dbc - prevDbc : 0.0f;
        const float dDc0 = finite && baselineValid ? dc0 - prevDc0 : 0.0f;
        const float dDc4 = finite && baselineValid ? dc4 - prevDc4 : 0.0f;
        const DWORD dtMs = lastLogTick != 0
            ? static_cast<DWORD>(now - lastLogTick) : 0u;

        spdlog::info(
            "WheelFFB XFORCE_NEIGHBORS t={} dtMs={} dbc={} dc0={} dc4={} dDbc={} dDc0={} dDc4={} speed={} carSteer={} lat264={} lat268={} finite={}",
            now, dtMs, dbc, dc0, dc4, dDbc, dDc0, dDc4,
            car->field_1C4, car->field_1D0, car->field_264, car->field_268,
            finite);

        lastLogTick = now;
        if (finite)
        {
            prevDbc = dbc;
            prevDc0 = dc0;
            prevDc4 = dc4;
            baselineValid = true;
        }
        else
        {
            baselineValid = false;
        }
    }
}
