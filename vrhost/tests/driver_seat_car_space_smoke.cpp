#include "vr/game/driver_seat_car_space.hpp"
#include <cmath>
#include <limits>
using namespace OutRunVR::DriverSeatCamera;
static bool near(float a, float b) {
    return std::fabs(a - b) < 0.0002f;
}
int main() {
    const CarAxes forwardZ{{0.f, 0.f, 1.f}, {0.f, 1.f, 0.f}};
    const Vec3 originalPos{0.f, 0.f, 0.f}, originalLook{0.f, 0.f, 10.f};
    Vec3 p{91.f, 92.f, 93.f}, l{94.f, 95.f, 96.f};
    if (!ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          forwardZ, -1.35f, -0.32f, 0.65f, p, l) ||
        !near(p.x, 0.32f) || !near(p.y, 0.65f) ||
        !near(p.z, -1.35f) || !near(l.z, 8.65f))
        return 1;
    // World yaw 90 degrees; offset must follow car rather than stay on
    // the native forward-Z camera basis.
    const CarAxes yaw90{{1.f, 0.f, 0.f}, {0.f, 1.f, 0.f}};
    if (!ComputeCarSpaceTranslatedCamera(originalPos,
          {10.f, 0.f, 1.f}, yaw90, -1.35f, -0.32f, 0.65f, p, l) ||
        !near(p.x, -1.35f) || !near(p.y, 0.65f) ||
        !near(p.z, -0.32f))
        return 2;
    // Reverse local car forward is corrected against the native camera.
    const CarAxes reverseZ{{0.f, 0.f, -1.f}, {0.f, 1.f, 0.f}};
    if (!ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          reverseZ, -1.35f, -0.32f, 0.65f, p, l) ||
        !near(p.x, 0.32f) || !near(p.z, -1.35f))
        return 3;
    const Vec3 oldP=p, oldL=l;
    const float nan=std::numeric_limits<float>::quiet_NaN();
    const float max=std::numeric_limits<float>::max();
    if (ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          {{0.f, 0.f, 0.f}, {0.f, 1.f, 0.f}},
          -1.35f, -.32f, .65f, p, l) ||
        ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          {{0.f, 1.f, 0.f}, {0.f, 1.f, 0.f}},
          -1.35f, -.32f, .65f, p, l) ||
        ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          {{1.f, 0.f, 0.f}, {0.f, 1.f, 0.f}},
          -1.35f, -.32f, .65f, p, l) ||
        ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          forwardZ, nan, -.32f, .65f, p, l) ||
        ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          forwardZ, max, 0.f, 0.f, p, l) ||
        ComputeCarSpaceTranslatedCamera({max, 0.f, 0.f},
          {max, 0.f, 0.f}, forwardZ, 1.f, 0.f, 0.f, p, l))
        return 4;
    // Fail closed without mutating either output on an invalid source pose.
    if (!near(p.x, oldP.x) || !near(p.y, oldP.y) ||
        !near(p.z, oldP.z) || !near(l.x, oldL.x) ||
        !near(l.z, oldL.z))
        return 5;
    // Direct recovery and camera-mode parity.
    if (!ComputeCarSpaceTranslatedCamera(originalPos, originalLook,
          forwardZ, -1.35f, -0.32f, 0.65f, p, l) ||
        !near(p.x, 0.32f))
        return 6;
    return 0;
}
