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

    inline float BlendBoost(float lower, float upper, float weight) noexcept
    {
        if (!std::isfinite(lower) || !std::isfinite(upper) ||
            !std::isfinite(weight) || upper <= lower)
            return lower;
        return lower + (upper - lower) * std::clamp(weight, 0.0f, 1.0f);
    }
}
