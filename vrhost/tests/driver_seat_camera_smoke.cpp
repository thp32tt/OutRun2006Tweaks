#include "vr/game/driver_seat_camera_math.hpp"
#include <cmath>
#include <limits>

using OutRunVR::DriverSeatCamera::Vec3;
using OutRunVR::DriverSeatCamera::ComputeTranslation;

static bool near(float value, float expected) { return std::fabs(value - expected) < 0.0001f; }

int main()
{
    // Do not use assert(): Release builds define NDEBUG. This executable
    // runs as an x64 host POST_BUILD gate and must fail CI on bad camera math.
    Vec3 delta{99.f, 88.f, 77.f};
    if (!ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 10.f},
            -1.35f, -0.32f, 0.65f, delta) ||
        !near(delta.x, 0.32f) || !near(delta.y, 0.65f) ||
        !near(delta.z, -1.35f))
        return 1;
    if (!ComputeTranslation({1.f, 2.f, 3.f}, {1.f, 3.f, 4.f},
            -1.35f, -0.32f, 0.65f, delta) ||
        !std::isfinite(delta.x) || !std::isfinite(delta.y) ||
        !std::isfinite(delta.z))
        return 2;

    const Vec3 saved = delta;
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    if (ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 0.f},
            0.f, 0.f, 0.f, delta) ||
        ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 1.f, 0.f},
            0.f, 0.f, 0.f, delta) ||
        ComputeTranslation({nan, 0.f, 0.f}, {0.f, 0.f, 1.f},
            0.f, 0.f, 0.f, delta) ||
        ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 1.f},
            inf, 0.f, 0.f, delta))
        return 3;
    if (!near(delta.x, saved.x) || !near(delta.y, saved.y) ||
        !near(delta.z, saved.z))
        return 4;

    // After a rejected pose, camera eligibility must recover immediately.
    if (!ComputeTranslation({0.f, 0.f, 0.f}, {0.f, 0.f, 10.f},
            -1.35f, -0.32f, 0.65f, delta) ||
        !near(delta.z, -1.35f))
        return 5;
    return 0;
}
