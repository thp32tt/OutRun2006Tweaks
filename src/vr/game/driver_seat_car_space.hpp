#pragma once
#include "driver_seat_camera_math.hpp"
#include <cmath>

namespace OutRunVR::DriverSeatCamera
{
    // Optional Quest-inspired body-space correction. The original PC car
    // matrix_B0 is the local->world owner; use its forward/up vectors, not
    // the smoothed bumper-view yaw, for offset placement. Do not change game
    // simulation camera, projection, tracking origin or XR eye offsets.
    struct CarAxes
    {
        Vec3 forward{};
        Vec3 up{};
    };

    inline bool ComputeCarSpaceTranslatedCamera(
        Vec3 position, Vec3 look, CarAxes axes,
        float forwardOffset, float rightOffset, float upOffset,
        Vec3& outPosition, Vec3& outLook) noexcept
    {
        const auto finite = [](Vec3 v) noexcept {
            return std::isfinite(v.x) && std::isfinite(v.y) &&
                std::isfinite(v.z);
        };
        if (!finite(position) || !finite(look) ||
            !finite(axes.forward) || !finite(axes.up) ||
            !std::isfinite(forwardOffset) || !std::isfinite(rightOffset) ||
            !std::isfinite(upOffset))
            return false;

        const auto norm = [&](Vec3 v, Vec3& n) noexcept {
            const double length = std::sqrt(
                double(v.x) * v.x + double(v.y) * v.y +
                double(v.z) * v.z);
            if (!std::isfinite(length) || length < 1.0e-5 ||
                length > 100.0)
                return false;
            n = {float(v.x / length), float(v.y / length),
                 float(v.z / length)};
            return finite(n);
        };
        const auto dot = [](Vec3 a, Vec3 b) noexcept {
            return double(a.x) * b.x + double(a.y) * b.y +
                double(a.z) * b.z;
        };
        const auto cross = [](Vec3 a, Vec3 b) noexcept {
            return Vec3{a.y * b.z - a.z * b.y,
                a.z * b.x - a.x * b.z,
                a.x * b.y - a.y * b.x};
        };

        Vec3 bodyForward{}, bodyUp{}, nativeForward{}, right{}, up{};
        if (!norm(axes.forward, bodyForward) ||
            !norm(axes.up, bodyUp) ||
            !norm({look.x - position.x, look.y - position.y,
                   look.z - position.z}, nativeForward))
            return false;
        if (std::fabs(dot(bodyForward, bodyUp)) > 0.2)
            return false;

        // Some vehicle models may use a reverse-facing local Z axis.
        // Align the car basis to the game's actual bumper camera and reject
        // sideways/unknown basis rather than teleporting the seat.
        const double alignment = dot(bodyForward, nativeForward);
        if (!std::isfinite(alignment) || std::fabs(alignment) < 0.25)
            return false;
        if (alignment < 0.0)
            bodyForward = {-bodyForward.x, -bodyForward.y, -bodyForward.z};

        // Preserve the project's existing (forward x up) "right" sign.
        if (!norm(cross(bodyForward, bodyUp), right) ||
            !norm(cross(right, bodyForward), up))
            return false;
        const double dx = double(bodyForward.x) * forwardOffset +
            double(right.x) * rightOffset + double(up.x) * upOffset;
        const double dy = double(bodyForward.y) * forwardOffset +
            double(right.y) * rightOffset + double(up.y) * upOffset;
        const double dz = double(bodyForward.z) * forwardOffset +
            double(right.z) * rightOffset + double(up.z) * upOffset;
        const Vec3 newPos{float(double(position.x) + dx),
                          float(double(position.y) + dy),
                          float(double(position.z) + dz)};
        const Vec3 newLook{float(double(look.x) + dx),
                           float(double(look.y) + dy),
                           float(double(look.z) + dz)};
        if (!finite(newPos) || !finite(newLook))
            return false;
        outPosition = newPos;
        outLook = newLook;
        return true;
    }
}
