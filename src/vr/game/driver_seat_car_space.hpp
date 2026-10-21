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


    // Quest-style cockpit owner: derive the seat anchor entirely from the
    // player-car local->world matrix. Unlike the legacy PC path, this does not
    // depend on the stock race camera eye/look pair, so native camera smoothing
    // or transition pulses cannot move the VR seat.
    inline bool ComputeCarAnchoredSeatPose(
        Vec3 carOrigin, CarAxes axes,
        float forwardOffset, float rightOffset, float upOffset,
        Vec3& outPosition, Vec3& outLook,
        float lookDistance = 1.0f) noexcept
    {
        const auto finite = [](Vec3 v) noexcept {
            return std::isfinite(v.x) && std::isfinite(v.y) &&
                std::isfinite(v.z);
        };
        if (!finite(carOrigin) || !finite(axes.forward) || !finite(axes.up) ||
            !std::isfinite(forwardOffset) || !std::isfinite(rightOffset) ||
            !std::isfinite(upOffset) || !std::isfinite(lookDistance) ||
            std::fabs(forwardOffset) > 10.0f ||
            std::fabs(rightOffset) > 10.0f ||
            std::fabs(upOffset) > 10.0f ||
            lookDistance < 0.05f || lookDistance > 100.0f)
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

        Vec3 forward{}, seedUp{}, right{}, up{};
        if (!norm(axes.forward, forward) || !norm(axes.up, seedUp) ||
            std::fabs(dot(forward, seedUp)) > 0.2 ||
            !norm(cross(forward, seedUp), right) ||
            !norm(cross(right, forward), up))
            return false;

        const Vec3 seat{
            float(double(carOrigin.x) + double(forward.x) * forwardOffset +
                  double(right.x) * rightOffset + double(up.x) * upOffset),
            float(double(carOrigin.y) + double(forward.y) * forwardOffset +
                  double(right.y) * rightOffset + double(up.y) * upOffset),
            float(double(carOrigin.z) + double(forward.z) * forwardOffset +
                  double(right.z) * rightOffset + double(up.z) * upOffset)
        };
        const Vec3 look{
            float(double(seat.x) + double(forward.x) * lookDistance),
            float(double(seat.y) + double(forward.y) * lookDistance),
            float(double(seat.z) + double(forward.z) * lookDistance)
        };
        if (!finite(seat) || !finite(look))
            return false;
        outPosition = seat;
        outLook = look;
        return true;
    }

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
            !std::isfinite(upOffset) ||
            std::fabs(forwardOffset) > 10.0f ||
            std::fabs(rightOffset) > 10.0f ||
            std::fabs(upOffset) > 10.0f)
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

    // Real vehicles can briefly expose a stale/sideways body basis during
    // camera transitions, respawn, collision and render interpolation.
    // Failing the whole cockpit test drops the car/passenger/near-plane
    // together for that frame, visibly flashing back into bumper view.
    // Keep the same owner by falling back to the *existing* validated
    // native-camera offset; never continue with partial car-space output.
    // Quest's cockpit body correction is scoped separately from the
    // original game's camera, so this is safer than using a stale matrix.
    inline bool ComputeStableSeatPose(
        Vec3 position, Vec3 look, bool preferCarSpace, CarAxes axes,
        float forwardOffset, float rightOffset, float upOffset,
        Vec3& outPosition, Vec3& outLook,
        bool* usedCarSpace = nullptr) noexcept
    {
        Vec3 candidatePosition{}, candidateLook{};
        const bool bodyAccepted = preferCarSpace &&
            ComputeCarSpaceTranslatedCamera(position, look, axes,
                forwardOffset, rightOffset, upOffset,
                candidatePosition, candidateLook);
        if (!bodyAccepted &&
            !ComputeTranslatedCamera(position, look, forwardOffset,
                rightOffset, upOffset, candidatePosition, candidateLook))
            return false;

        // Atomic pair: failure leaves both destination vectors untouched.
        outPosition = candidatePosition;
        outLook = candidateLook;
        if (usedCarSpace)
            *usedCarSpace = bodyAccepted;
        return true;
    }
}