#pragma once
#include <cmath>

namespace OutRunVR::DriverSeatVehicle
{
    // Apply a *visual-only* uniform scale to the temporary matrix passed
    // by DispCarModel_Common to the game's matrix stack. The car's world
    // translation must remain unchanged; never edit EVWORK_CAR::matrix_B0,
    // collision, physics, camera or any model asset on disk.
    //
    // The Quest cockpit_body_correction is a 4x4 render transform. The APK
    // does not yet establish a fixed uniform vehicle-scale number, so this
    // is an explicit PCVR user-calibration layer, not an asserted APK port.
    template <typename Matrix>
    inline bool TryScaleModelBasis(Matrix& matrix, float scale) noexcept
    {
        if (!std::isfinite(scale) || scale < 0.85f || scale > 1.35f)
            return false;
        const float input[9] = {
            matrix._11, matrix._12, matrix._13,
            matrix._21, matrix._22, matrix._23,
            matrix._31, matrix._32, matrix._33
        };
        float scaled[9]{};
        for (unsigned i = 0; i < 9; ++i)
        {
            if (!std::isfinite(input[i]))
                return false;
            scaled[i] = input[i] * scale;
            if (!std::isfinite(scaled[i]))
                return false;
        }
        if (!std::isfinite(matrix._41) || !std::isfinite(matrix._42) ||
            !std::isfinite(matrix._43) || !std::isfinite(matrix._44))
            return false;
        matrix._11 = scaled[0]; matrix._12 = scaled[1]; matrix._13 = scaled[2];
        matrix._21 = scaled[3]; matrix._22 = scaled[4]; matrix._23 = scaled[5];
        matrix._31 = scaled[6]; matrix._32 = scaled[7]; matrix._33 = scaled[8];
        return true;
    }
}
