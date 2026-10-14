#pragma once
#include <algorithm>
#include <cmath>

// Only exact-producer gameplay HUD groups use this binocular source-space
// interpolation. Leave F11, pause/ESC, world and GOAL/+TIME at baseline.
namespace OutRunVrHudEdge
{
    inline float PeripheralWeight(float ndc) noexcept
    {
        if (!std::isfinite(ndc))
            return 0.0f;
        const float distance = std::fabs(ndc);
        if (distance <= 0.35f || distance > 1.20f)
            return 0.0f;
        if (distance >= 0.60f)
            return 1.0f;
        const float t = (distance - 0.35f) / 0.25f;
        // C1-continuous entry removes both the original anchor jump and
        // optical-size jump at the old hard |NDC| 0.40 threshold.
        return t * t * (3.0f - 2.0f * t);
    }

    inline float PeripheralAnchor(float ndc, float limit) noexcept
    {
        if (!std::isfinite(limit) || limit <= 0.0f)
            return 0.0f;
        const float weight = PeripheralWeight(ndc);
        if (weight == 0.0f)
            return 0.0f;
        return std::clamp(ndc, -limit, limit) * weight;
    }

    // Smooth each exact gameplay glyph group's entrance/exit over a bounded
    // fraction of source space before the stereo-common anchor/zoom engages.
    inline float FullyVisibleWeight(
        float leftInset, float rightInset, float topInset, float bottomInset,
        float sourceWidth, float sourceHeight) noexcept
    {
        if (!std::isfinite(leftInset) || !std::isfinite(rightInset) ||
            !std::isfinite(topInset) || !std::isfinite(bottomInset) ||
            !std::isfinite(sourceWidth) || !std::isfinite(sourceHeight) ||
            sourceWidth <= 0.0f || sourceHeight <= 0.0f)
            return 0.0f;
        const float x = std::clamp(
            (std::min)(leftInset, rightInset) / (0.015f * sourceWidth),
            0.0f, 1.0f);
        const float y = std::clamp(
            (std::min)(topInset, bottomInset) / (0.015f * sourceHeight),
            0.0f, 1.0f);
        const float t = (std::min)(x, y);
        return t * t * (3.0f - 2.0f * t);
    }

    inline float BlendBoost(float lower, float upper, float weight) noexcept
    {
        if (!std::isfinite(lower) || !std::isfinite(upper) ||
            !std::isfinite(weight) || upper <= lower)
            return lower;
        return lower + (upper - lower) * std::clamp(weight, 0.0f, 1.0f);
    }
}
