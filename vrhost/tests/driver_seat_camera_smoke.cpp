#include "vr/game/driver_seat_camera_math.hpp"
#include <cassert>
#include <cmath>
#include <limits>

using OutRunVR::DriverSeatCamera::Vec3;
using OutRunVR::DriverSeatCamera::ComputeTranslation;

static bool near(float value, float expected) { return std::fabs(value - expected) < 0.0001f; }

int main()
{
    Vec3 delta{99.f, 88.f, 77.f};
    // Preserve the exact established sign of the cockpit preset.
    assert(ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 10.f},
        -1.35f, -0.32f, 0.65f, delta));
    assert(near(delta.x, 0.32f) && near(delta.y, 0.65f) && near(delta.z, -1.35f));
    assert(ComputeTranslation({1.f, 2.f, 3.f}, {1.f, 3.f, 4.f},
        -1.35f, -0.32f, 0.65f, delta));
    assert(std::isfinite(delta.x) && std::isfinite(delta.y) && std::isfinite(delta.z));
    const Vec3 saved = delta;
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    assert(!ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 0.f}, 0.f, 0.f, 0.f, delta));
    assert(!ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 1.f, 0.f}, 0.f, 0.f, 0.f, delta));
    assert(!ComputeTranslation({nan, 0.f, 0.f}, {0.f, 0.f, 1.f}, 0.f, 0.f, 0.f, delta));
    assert(!ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 1.f}, inf, 0.f, 0.f, delta));
    assert(near(delta.x, saved.x) && near(delta.y, saved.y) && near(delta.z, saved.z));
}
