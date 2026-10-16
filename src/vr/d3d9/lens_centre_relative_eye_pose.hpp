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

    // OpenXR supplies head-local eye rotations, not world-space head poses.
    // R84 C993 already removed the common head inverse; keep per-eye cant.
    // Publish neither eye when any pose input is malformed.
    inline bool BuildHeadRelativeEyePose(
        const float (&eyeOffsets)[2][3],
        const float (&eyeOrientations)[2][4],
        float (&relativeOffsets)[2][3],
        float (&relativeOrientations)[2][4]) noexcept
    {
        float candidateOffsets[2][3]{};
        if (!BuildHeadRelativeEyeOffsets(eyeOffsets, candidateOffsets))
            return false;
        float candidateOrientations[2][4]{};
        for (int eye = 0; eye < 2; ++eye)
        {
            double normSquared = 0.0;
            for (int axis = 0; axis < 4; ++axis)
            {
                if (!std::isfinite(eyeOrientations[eye][axis]))
                    return false;
                const double value = eyeOrientations[eye][axis];
                normSquared += value * value;
            }
            if (!std::isfinite(normSquared) ||
                normSquared < 1.0e-8 || normSquared > 16.0)
                return false;
            const double inverseLength = 1.0 / std::sqrt(normSquared);
            for (int axis = 0; axis < 4; ++axis)
            {
                candidateOrientations[eye][axis] = static_cast<float>(
                    static_cast<double>(eyeOrientations[eye][axis]) * inverseLength);
                if (!std::isfinite(candidateOrientations[eye][axis]))
                    return false;
            }
        }
        for (int eye = 0; eye < 2; ++eye)
        {
            for (int axis = 0; axis < 3; ++axis)
                relativeOffsets[eye][axis] = candidateOffsets[eye][axis];
            for (int axis = 0; axis < 4; ++axis)
                relativeOrientations[eye][axis] = candidateOrientations[eye][axis];
        }
        return true;
    }

}
