#pragma once
// Bound OutRun 2006 original 9/11/13-stride menu quad size by the
// CURRENT viewport, not the old cached screen scale after resize/Reset.
#include <cmath>
namespace OutRunVrUiAspect {
inline float BoundedMultiSpriteContainScale(
    float sx, float sy, float width, float height,
    float originalWidth, float originalHeight) noexcept
{
    if (!std::isfinite(sx) || !std::isfinite(sy) ||
        !std::isfinite(width) || !std::isfinite(height) ||
        !std::isfinite(originalWidth) || !std::isfinite(originalHeight) ||
        sx <= 1.0e-6f || sy <= 1.0e-6f ||
        width <= 0.0f || height <= 0.0f ||
        originalWidth <= 0.0f || originalHeight <= 0.0f)
        return 0.0f;
    const double physicalX = double(width) / originalWidth;
    const double physicalY = double(height) / originalHeight;
    const double requested = sx < sy ? double(sx) : double(sy);
    const double physical = physicalX < physicalY ? physicalX : physicalY;
    const double bounded = requested < physical ? requested : physical;
    if (!std::isfinite(bounded) || !(bounded > 0.0) ||
        bounded > 3.402823466e38)
        return 0.0f;
    const float result = static_cast<float>(bounded);
    return std::isfinite(result) && result > 0.0f ? result : 0.0f;
}
}
