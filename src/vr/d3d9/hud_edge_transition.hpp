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
        if (distance <= 0.35f || distance >= 1.20f)
            return 0.0f;
        // The old >1.20 cutoff changed a full peripheral anchor/zoom to
        // zero in one draw. Ease the exact gameplay-HUD owner back to neutral
        // outside the visible source instead of snapping at the crop edge.
        // Keep the central 0.35..0.60 entry and 0.60..1.00 core unchanged.
        if (distance >= 1.0f)
        {
            const float t = (distance - 1.0f) / 0.20f;
            return 1.0f - t * t * (3.0f - 2.0f * t);
        }
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

    // R84 exact peripheral gameplay HUD enters the finite binocular path
    // before the legacy 2D affine anchor code. Form source NDC only once:
    // independent per-eye projection must consume the SAME shifted pixel.
    // No generic ScreenHud, +TIME, GOAL, world or external F11 admission.
    inline bool RemapFiniteHudPixel(
        float x, float y, float vx, float vy, float width, float height,
        float hudScale, float boost, float anchorX, float anchorY,
        float& outX, float& outY) noexcept
    {
        if (!std::isfinite(x) || !std::isfinite(y) ||
            !std::isfinite(vx) || !std::isfinite(vy) ||
            !std::isfinite(width) || !std::isfinite(height) ||
            !std::isfinite(hudScale) || !std::isfinite(boost) ||
            !std::isfinite(anchorX) || !std::isfinite(anchorY) ||
            width <= 0.f || height <= 0.f || hudScale <= 0.f ||
            boost < 1.f || boost > 3.f ||
            std::fabs(anchorX) > .82f || std::fabs(anchorY) > .78f)
            return false;
        const double cx = double(vx) + double(width) * .5;
        const double cy = double(vy) + double(height) * .5;
        const double scale = double(hudScale) * double(boost);
        const double ndcX = (double(x) - cx) * (2. / double(width));
        const double ndcY = (cy - double(y)) * (2. / double(height));
        const double px = cx + double(width) * .5 *
            (scale * ndcX + (1. - scale) * double(anchorX));
        const double py = cy - double(height) * .5 *
            (scale * ndcY + (1. - scale) * double(anchorY));
        if (!std::isfinite(px) || !std::isfinite(py))
            return false;
        const float stagedX = static_cast<float>(px);
        const float stagedY = static_cast<float>(py);
        if (!std::isfinite(stagedX) || !std::isfinite(stagedY))
            return false;
        outX = stagedX;
        outY = stagedY;
        return true;
    }
}
