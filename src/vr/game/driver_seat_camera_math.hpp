#pragma once

#include <cmath>

namespace OutRunVR::DriverSeatCamera
{
    struct Vec3
    {
        float x{};
        float y{};
        float z{};
    };

    // Pure game-camera-space translation: never alters the native camera state.
    // Keep the established camera-relative right-axis convention for current
    // DriverSeatRight presets. Invalid camera poses/INI values fail closed.
    inline bool ComputeTranslation(Vec3 position, Vec3 look,
        float forward, float right, float up, Vec3& translation) noexcept
    {
        if (!std::isfinite(position.x) || !std::isfinite(position.y) ||
            !std::isfinite(position.z) || !std::isfinite(look.x) ||
            !std::isfinite(look.y) || !std::isfinite(look.z) ||
            !std::isfinite(forward) || !std::isfinite(right) ||
            !std::isfinite(up))
            return false;

        float fx = look.x - position.x;
        float fy = look.y - position.y;
        float fz = look.z - position.z;
        const float forwardLength = std::sqrt(fx * fx + fy * fy + fz * fz);
        if (!std::isfinite(forwardLength) || forwardLength < 1.0e-5f)
            return false;
        fx /= forwardLength;
        fy /= forwardLength;
        fz /= forwardLength;

        // Forward x world-up preserves the existing PCVR offset sign.
        // A vertical pole has no stable right axis. Fail closed rather than
        // hiding the driver with a mismatched camera.
        float rx = -fz;
        float rz = fx;
        const float rightLength = std::sqrt(rx * rx + rz * rz);
        if (!std::isfinite(rightLength) || rightLength < 1.0e-5f)
            return false;
        rx /= rightLength;
        rz /= rightLength;
        const float ux = -rz * fy;
        const float uy = rz * fx - rx * fz;
        const float uz = rx * fy;
        const Vec3 proposed{
            fx * forward + rx * right + ux * up,
            fy * forward + uy * up,
            fz * forward + rz * right + uz * up
        };
        if (!std::isfinite(proposed.x) || !std::isfinite(proposed.y) ||
            !std::isfinite(proposed.z))
            return false;
        translation = proposed;
        return true;
    }
    // Scope contract: cockpit near-plane, player-car model, driver suppression
    // and camera displacement must agree for the *same* native camera frame.
    // Re-evaluate after mode switches; never reuse a cached eligibility bit.
    inline bool CameraAndBodyEligible(
        bool enabled, bool gameplayActive, float transitionTime,
        int nativeMode, int selectedMode, Vec3 position, Vec3 look,
        float forward, float right, float up) noexcept
    {
        if (!enabled || !gameplayActive || nativeMode != selectedMode ||
            !std::isfinite(transitionTime) || transitionTime != 0.0f)
            return false;
        Vec3 ignored{};
        return ComputeTranslation(position, look, forward, right, up, ignored);
    }

}
