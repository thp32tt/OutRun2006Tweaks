#pragma once
#include <cmath>
// Opt-in center-content crop for the captured, already-letterboxed 4:3
// OutRun menu. The LOCAL-fixed two-eye clip must use the SAME resulting
// content aspect and UV, not the ultrawide desktop aspect with black rails.
namespace OutRunVrMenuAspect
{
    struct CropPlan
    {
        bool crop = false;
        float offsetX = 0.0f;  // fraction of the captured game client width
        float width = 1.0f;
        float aspect = 0.0f;
    };

    // Projection spans are linear in tan(FOV), not in the angles themselves.
    // Averaging angles before tan() changes apparent menu aspect when OpenXR
    // publishes asymmetric left/right eye tangents (Quest3/VDXR).
    struct CommonFovTangents
    {
        bool valid = false;
        float left = 0.0f, right = 0.0f;
        float down = 0.0f, up = 0.0f;
    };

    inline CommonFovTangents PlanCommonFovTangents(
        float left0, float right0, float down0, float up0,
        float left1, float right1, float down1, float up1) noexcept
    {
        const float angles[8]{
            left0, right0, down0, up0, left1, right1, down1, up1
        };
        // tan() becomes ill-conditioned at +/-pi/2. Reject invalid or
        // near-pole XR publications rather than distorting the menu for one
        // stale/recentered eye. Do not use one eye's span as a false pair.
        for (const float angle : angles)
            if (!std::isfinite(angle) || std::fabs(angle) >= 1.55f)
                return {};

        const float l0 = std::tan(left0), r0 = std::tan(right0);
        const float d0 = std::tan(down0), u0 = std::tan(up0);
        const float l1 = std::tan(left1), r1 = std::tan(right1);
        const float d1 = std::tan(down1), u1 = std::tan(up1);
        if (!(r0 - l0 > 0.05f && r1 - l1 > 0.05f &&
              u0 - d0 > 0.05f && u1 - d1 > 0.05f))
            return {};

        const float left = 0.5f * (l0 + l1);
        const float right = 0.5f * (r0 + r1);
        const float down = 0.5f * (d0 + d1);
        const float up = 0.5f * (u0 + u1);
        if (!std::isfinite(left) || !std::isfinite(right) ||
            !std::isfinite(down) || !std::isfinite(up) ||
            right - left <= 0.05f || up - down <= 0.05f)
            return {};
        return { true, left, right, down, up };
    }

    constexpr CropPlan PlanCenteredContent(
        float sourceAspect, float intendedAspect) noexcept
    {
        // Reject NaN/Inf, invalid client sizes and nonsensical overrides.
        // Failing closed preserves the existing complete-client projection.
        if (!(sourceAspect >= 0.5f && sourceAspect <= 5.0f) ||
            !(intendedAspect >= 0.5f && intendedAspect <= 4.0f) ||
            sourceAspect <= intendedAspect)
            return { false, 0.0f, 1.0f, sourceAspect };

        const float width = intendedAspect / sourceAspect;
        return { true, (1.0f - width) * 0.5f, width, intendedAspect };
    }
}
