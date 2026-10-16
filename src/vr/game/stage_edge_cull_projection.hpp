#pragma once
// Original CalcBall3D2D 4:3 edge-culling correction shared by desktop and
// DX9Ex R84. Source viewport may be transiently unpublished during Reset.
// This helper never changes game visibility if either component is untrusted.
#include <cmath>

namespace OutRunVrStageCull
{
    struct BallProjection
    {
        float x = 0.0f;
        float y = 0.0f;
        bool valid = false;
    };

    inline BallProjection CorrectBallProjection(float originalX,
        float originalY, float sourceWidth, float sourceHeight) noexcept
    {
        if (!std::isfinite(originalX) || !std::isfinite(originalY) ||
            !std::isfinite(sourceWidth) || !std::isfinite(sourceHeight) ||
            sourceWidth <= 0.0f || sourceHeight <= 0.0f)
            return {};

        constexpr float NativeAspect = 4.0f / 3.0f;
        const float sourceAspect = sourceWidth / sourceHeight;
        if (!std::isfinite(sourceAspect) || sourceAspect <= 0.0f)
            return {};

        // Preserve the original correction arithmetic/order for a valid
        // viewport, including wide and portrait resolutions. Stage both
        // results before the original game's Sphere is ever modified.
        const float correctedX = (originalX / sourceAspect) * NativeAspect;
        const float correctedY = (originalY * sourceAspect) / NativeAspect;
        if (!std::isfinite(correctedX) || !std::isfinite(correctedY))
            return {};
        return {correctedX, correctedY, true};
    }
}
