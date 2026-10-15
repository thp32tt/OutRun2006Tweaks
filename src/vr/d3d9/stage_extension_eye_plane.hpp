#pragma once

// Portable row-vector 4x4 homogeneous transform for the exact +TIME
// XYZRHW producer. The R84 caller constructs the finite HUD plane with
// its latched head inverse and both per-eye projection matrices.
#include <cmath>

namespace OutRunVR::StageExtensionPlane
{
    inline bool ProjectPixel(
        const float clipFromGameNdc[16], float sourceX, float sourceY,
        float viewportX, float viewportY, float viewportWidth,
        float viewportHeight, float hudScale,
        float& eyeX, float& eyeY) noexcept
    {
        if (!clipFromGameNdc || !std::isfinite(sourceX) ||
            !std::isfinite(sourceY) || !std::isfinite(viewportX) ||
            !std::isfinite(viewportY) || !std::isfinite(viewportWidth) ||
            !std::isfinite(viewportHeight) || !std::isfinite(hudScale) ||
            viewportWidth <= 0.0f || viewportHeight <= 0.0f ||
            hudScale <= 0.0f)
            return false;
        const float nx = ((sourceX - viewportX) * 2.0f /
                          viewportWidth - 1.0f) * hudScale;
        const float ny = (1.0f - (sourceY - viewportY) * 2.0f /
                          viewportHeight) * hudScale;
        const float x = nx * clipFromGameNdc[0] +
            ny * clipFromGameNdc[4] + clipFromGameNdc[12];
        const float y = nx * clipFromGameNdc[1] +
            ny * clipFromGameNdc[5] + clipFromGameNdc[13];
        const float w = nx * clipFromGameNdc[3] +
            ny * clipFromGameNdc[7] + clipFromGameNdc[15];
        if (!std::isfinite(x) || !std::isfinite(y) ||
            !std::isfinite(w) || w <= 1.0e-5f)
            return false;
        const float newX = viewportX + (x / w + 1.0f) *
            0.5f * viewportWidth;
        const float newY = viewportY + (1.0f - y / w) *
            0.5f * viewportHeight;
        if (!std::isfinite(newX) || !std::isfinite(newY))
            return false;
        eyeX = newX;
        eyeY = newY;
        return true;
    }
}
