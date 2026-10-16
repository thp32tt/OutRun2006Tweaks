#pragma once
#include "lens_centre_relative_eye_pose.hpp"
#include <cmath>

// Exact R84 ScreenHud *shader* c64 plane. The source game WVP is first
// recovered independently of the live injected c64 and the common head
// inverse is applied once by R30. Only HEAD-LOCAL OpenXR eye pose remains.
// Reuse the same normalized, bilateral-only eye-pair admission as the C993
// flare, +TIME/GOAL fixed-function sprites, and Calc3D2D rank markers.
namespace OutRunVR::HudShaderEyes
{
    struct PosePair
    {
        float offset[2][3]{};
        float orientation[2][4]{};
    };

    inline bool Build(const float (&offsets)[2][3],
        const float (&orientations)[2][4], float worldScale,
        PosePair& output) noexcept
    {
        if (!std::isfinite(worldScale) || worldScale <= 0.0f)
            return false;
        PosePair candidate{};
        if (!OutRunVR::LensCentre::BuildHeadRelativeEyePose(
                offsets, orientations, candidate.offset,
                candidate.orientation))
            return false;
        output = candidate;
        return true;
    }
}
