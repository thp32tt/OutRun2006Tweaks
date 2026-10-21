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

    // Matching cockpit render and near-clip eligibility is a shared
    // per-frame condition, not independent ad-hoc checks in two hooks.
    using OutRunVR::DriverSeatCamera::CameraAndBodyEligible;
    const Vec3 nativePos{0.f, 0.f, 0.f}, nativeLook{0.f, 0.f, 10.f};
    if (!CameraAndBodyEligible(true, true, 0.f, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f))
        return 6;
    if (CameraAndBodyEligible(false, true, 0.f, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f) ||
        CameraAndBodyEligible(true, false, 0.f, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f) ||
        CameraAndBodyEligible(true, true, 0.1f, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f) ||
        CameraAndBodyEligible(true, true, inf, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f) ||
        CameraAndBodyEligible(true, true, 0.f, 2, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f) ||
        CameraAndBodyEligible(true, true, 0.f, 1, 1,
            nativePos, nativeLook, -1.35f, nan, 0.65f))
        return 7;
    if (!CameraAndBodyEligible(true, true, 0.f, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f))
        return 8;
    // Reject overflow on the final absolute seat camera, even with a
    // finite local offset. Eligibility, car body and near clip must agree.
    using OutRunVR::DriverSeatCamera::ComputeTranslatedCamera;
    const float maxf = std::numeric_limits<float>::max();
    Vec3 posOut{12.f, 13.f, 14.f}, lookOut{15.f, 16.f, 17.f};
    if (ComputeTranslatedCamera({maxf * 0.5f, 0.f, 0.f},
            {maxf, 0.f, 0.f}, maxf, 0.f, 0.f, posOut, lookOut))
        return 9;
    if (!near(posOut.x, 12.f) || !near(lookOut.z, 17.f))
        return 10;
    if (CameraAndBodyEligible(true, true, 0.f, 1, 1,
            {maxf * 0.5f, 0.f, 0.f}, {maxf, 0.f, 0.f},
            maxf, 0.f, 0.f))
        return 11;
    if (!ComputeTranslatedCamera({0.f, 0.f, 0.f}, {0.f, 0.f, 10.f},
            -1.35f, -0.32f, 0.65f, posOut, lookOut) ||
        !near(posOut.x, 0.32f) || !near(posOut.y, 0.65f) ||
        !near(posOut.z, -1.35f) || !near(lookOut.x, 0.32f) ||
        !near(lookOut.y, 0.65f) || !near(lookOut.z, 8.65f))
        return 12;

    using OutRunVR::DriverSeatCamera::SafeNearPlane;
    // A NaN hot-edited INI near-plane previously poisoned both stereo
    // projection matrices; reject it and recover on the next valid frame.
    if (!near(SafeNearPlane(0.1f,0.05f,0.15f),0.1f) ||
        !near(SafeNearPlane(0.01f,0.05f,0.15f),0.05f) ||
        !near(SafeNearPlane(0.35f,0.05f,0.15f),0.15f) ||
        !near(SafeNearPlane(nan,0.05f,0.15f),0.10f) ||
        !near(SafeNearPlane(inf,0.05f,0.15f),0.10f) ||
        !near(SafeNearPlane(-inf,0.05f,0.15f),0.10f) ||
        !near(SafeNearPlane(0.f,0.05f,0.15f),0.10f) ||
        !near(SafeNearPlane(nan,0.03f,0.50f),0.10f))
        return 13;
    if (!near(SafeNearPlane(0.08f,0.05f,0.15f),0.08f))
        return 14;
    // Independent original camera mode counters (+0x340/+0x344) must
    // settle before any synthetic seat camera can be admitted.
    using OutRunVR::DriverSeatCamera::NativeViewTransitionSettled;
    if (!NativeViewTransitionSettled(0, 0) ||
        NativeViewTransitionSettled(1, 0) ||
        NativeViewTransitionSettled(0, 1) ||
        NativeViewTransitionSettled(5, 2) ||
        NativeViewTransitionSettled(0xffff, 0))
        return 15;
    if (!NativeViewTransitionSettled(0, 0) ||
        !CameraAndBodyEligible(true, true, 0.f, 1, 1,
            nativePos, nativeLook, -1.35f, -0.32f, 0.65f))
        return 16;

    // Once a selected native view has fully settled, transient pulses of the
    // secondary +0x340/+0x344 counters must not eject the cockpit for one
    // frame and create a visible zoom/pullback cycle. A real mode/timer
    // transition still clears the latch and requires a fresh settled sample.
    using OutRunVR::DriverSeatCamera::StableNativeViewEligible;
    bool settledLatch = false;
    if (StableNativeViewEligible(true, true, 0.f, 1, 1, 1, 0,
            settledLatch) || settledLatch)
        return 17;
    if (!StableNativeViewEligible(true, true, 0.f, 1, 1, 0, 0,
            settledLatch) || !settledLatch)
        return 18;
    if (!StableNativeViewEligible(true, true, 0.f, 1, 1, 2, 0,
            settledLatch) ||
        !StableNativeViewEligible(true, true, 0.f, 1, 1, 0, 3,
            settledLatch) || !settledLatch)
        return 19;
    if (StableNativeViewEligible(true, true, 1.f, 1, 1, 0, 0,
            settledLatch) || settledLatch)
        return 20;
    if (StableNativeViewEligible(true, true, 0.f, 1, 1, 5, 0,
            settledLatch) || settledLatch)
        return 21;
    if (!StableNativeViewEligible(true, true, 0.f, 1, 1, 0, 0,
            settledLatch) || !settledLatch)
        return 22;
    if (StableNativeViewEligible(true, true, 0.f, 2, 1, 0, 0,
            settledLatch) || settledLatch)
        return 23;
    return 0;
}