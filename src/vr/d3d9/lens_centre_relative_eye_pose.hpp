#pragma once
#include <cmath>

// R84 C993 central flare: original game WVP is transformed by the latched
// head inverse exactly once. Only interocular offsets remain at the eye stage;
// absolute HMD translations/orientations must not be applied a second time.
namespace OutRunVR::LensCentre
{
    inline bool BuildHeadRelativeEyeOffsets(
        const float (&absolute)[2][3], float (&relative)[2][3]) noexcept
    {
        float candidate[2][3]{};
        for (int axis = 0; axis < 3; ++axis)
        {
            if (!std::isfinite(absolute[0][axis]) ||
                !std::isfinite(absolute[1][axis]))
                return false;
            // Widen before averaging: a distant tracking origin must not
            // overflow float even if both valid eyes have finite offsets.
            const double centre =
                (static_cast<double>(absolute[0][axis]) +
                 static_cast<double>(absolute[1][axis])) * 0.5;
            for (int eye = 0; eye < 2; ++eye)
            {
                candidate[eye][axis] = static_cast<float>(
                    static_cast<double>(absolute[eye][axis]) - centre);
                if (!std::isfinite(candidate[eye][axis]))
                    return false;
            }
        }
        // Failed pose inputs leave both previously published eyes untouched.
        for (int eye = 0; eye < 2; ++eye)
            for (int axis = 0; axis < 3; ++axis)
                relative[eye][axis] = candidate[eye][axis];
        return true;
    }
}
