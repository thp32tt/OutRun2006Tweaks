#pragma once
#include "driver_seat_camera_math.hpp"
#include <cmath>

namespace OutRunVR::DriverSeatCamera
{
    // Cockpit-only yaw correction. Preserve the current native camera's eye
    // position, pitch and look distance; use the player-car body for yaw only.
    // Vehicle forward polarity is selected once per player/session to avoid
    // an abrupt 180-degree turn during drifting or camera interpolation.
    // Neither game simulation camera nor XR head/eye poses are modified.
    inline bool ComputeVehicleLockedYawLook(
        Vec3 cameraPosition, Vec3 currentLook,
        Vec3 carForward, Vec3 carUp, int& forwardPolarity,
        Vec3& outLook) noexcept
    {
        const auto finite = [](Vec3 v) noexcept {
            return std::isfinite(v.x) && std::isfinite(v.y) &&
                std::isfinite(v.z);
        };
        if (!finite(cameraPosition) || !finite(currentLook) ||
            !finite(carForward) || !finite(carUp) ||
            (forwardPolarity != 0 && forwardPolarity != 1 &&
             forwardPolarity != -1))
            return false;

        const double dx = double(currentLook.x) - cameraPosition.x;
        const double dy = double(currentLook.y) - cameraPosition.y;
        const double dz = double(currentLook.z) - cameraPosition.z;
        const double lookLength = std::sqrt(dx*dx + dy*dy + dz*dz);
        const double lookHorizontal = std::hypot(dx, dz);
        const double carLength = std::sqrt(
            double(carForward.x)*carForward.x +
            double(carForward.y)*carForward.y +
            double(carForward.z)*carForward.z);
        const double carUpLength = std::sqrt(
            double(carUp.x)*carUp.x +
            double(carUp.y)*carUp.y +
            double(carUp.z)*carUp.z);
        const double carHorizontal = std::hypot(
            double(carForward.x), double(carForward.z));
        if (!std::isfinite(lookLength) || lookLength < 1.0e-5 ||
            !std::isfinite(lookHorizontal) || lookHorizontal < 1.0e-5 ||
            !std::isfinite(carLength) || carLength < 1.0e-5 ||
            !std::isfinite(carUpLength) || carUpLength < 1.0e-5 ||
            !std::isfinite(carHorizontal) || carHorizontal < 1.0e-5)
            return false;
        const double orthogonality = (
            double(carForward.x)*carUp.x +
            double(carForward.y)*carUp.y +
            double(carForward.z)*carUp.z) / (carLength*carUpLength);
        if (!std::isfinite(orthogonality) ||
            std::fabs(orthogonality) > 0.2)
            return false;

        int sign = forwardPolarity;
        if (sign == 0)
        {
            const double alignment =
                (dx*carForward.x + dz*carForward.z) /
                (lookHorizontal*carHorizontal);
            // Do not learn a 180-degree polarity from a sideways native
            // view during a camera transition. Try again next valid frame.
            if (!std::isfinite(alignment) || std::fabs(alignment) < 0.5)
                return false;
            sign = alignment > 0.0 ? 1 : -1;
        }
        const double hx = sign*double(carForward.x)/carHorizontal;
        const double hz = sign*double(carForward.z)/carHorizontal;
        const Vec3 candidate{
            float(cameraPosition.x + lookHorizontal*hx),
            float(cameraPosition.y + dy),
            float(cameraPosition.z + lookHorizontal*hz)
        };
        if (!finite(candidate))
            return false;
        outLook = candidate;
        forwardPolarity = sign;
        return true;
    }
}
