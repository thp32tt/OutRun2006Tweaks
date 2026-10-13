#pragma once
#include <cmath>

// Only the original OutRun ESC/pause shell and its exact arrow sprites opt in.
// Shared head-forward tangent centre corrects vertical XR FOV asymmetry; both
// eyes fall back to the original neutral transform on invalid publications.
namespace OutRunVrPauseEye
{
    struct VerticalAffine
    {
        float scale[2]{1.0f, 1.0f};
        float offset[2]{0.0f, 0.0f};
        bool valid = false;
    };

    inline VerticalAffine Compute(
        float leftDown, float leftUp, float rightDown, float rightUp) noexcept
    {
        const float downs[2]{leftDown, rightDown};
        const float ups[2]{leftUp, rightUp};
        float span[2]{}, sum[2]{};
        for (int eye = 0; eye < 2; ++eye)
        {
            if (!std::isfinite(downs[eye]) || !std::isfinite(ups[eye]) ||
                downs[eye] >= ups[eye])
                return {};
            const float tDown = std::tan(downs[eye]);
            const float tUp = std::tan(ups[eye]);
            span[eye] = tUp - tDown;
            sum[eye] = tUp + tDown;
            if (!std::isfinite(span[eye]) || !std::isfinite(sum[eye]) ||
                span[eye] <= 0.05f || span[eye] > 10.0f)
                return {};
        }
        const float common = 0.5f * (span[0] + span[1]);
        VerticalAffine result{};
        for (int eye = 0; eye < 2; ++eye)
        {
            const float s = common / span[eye];
            const float o = -sum[eye] / span[eye];
            if (!std::isfinite(s) || !std::isfinite(o) ||
                s < 0.50f || s > 1.50f || std::fabs(o) > 0.50f)
                return {};
            result.scale[eye] = s;
            result.offset[eye] = o;
        }
        result.valid = true;
        return result;
    }
}
