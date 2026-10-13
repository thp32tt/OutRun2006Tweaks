#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
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


    // A 2D quad centered at NDC (0,0) is NOT centered on the forward ray
    // when OpenXR publishes asymmetric FOV. Place the LOCAL-fixed menu on
    // tan(angle)=0 and contain it INSIDE the remaining visible FOV. Both
    // eyes use the same rectangle and common tangent-plane projection.
    struct OpticalClipPlan
    {
        bool valid = false;
        float centerX = 0.0f, centerY = 0.0f;
        float halfWidth = 0.0f, halfHeight = 0.0f;
    };

    inline OpticalClipPlan PlanOpticallyCenteredClip(
        const CommonFovTangents& fov, float sourceAspect) noexcept
    {
        if (!fov.valid || !std::isfinite(sourceAspect) ||
            sourceAspect < 0.5f || sourceAspect > 5.0f ||
            !std::isfinite(fov.left) || !std::isfinite(fov.right) ||
            !std::isfinite(fov.down) || !std::isfinite(fov.up))
            return {};

        const float spanX = fov.right - fov.left;
        const float spanY = fov.up - fov.down;
        if (!std::isfinite(spanX) || !std::isfinite(spanY) ||
            spanX <= 0.05f || spanY <= 0.05f)
            return {};

        // In an asymmetric projection, NDC of tan(X/Y)=0 is displaced.
        // A missing forward ray (e.g. stale/invalid single-eye FOV) must
        // not shift the quad outside the display or produce negative space.
        const float centerX = -(fov.left + fov.right) / spanX;
        const float centerY = -(fov.down + fov.up) / spanY;
        const float requiredRatio = sourceAspect * (spanY / spanX);
        if (!std::isfinite(centerX) || !std::isfinite(centerY) ||
            !std::isfinite(requiredRatio) || requiredRatio <= 0.0f ||
            std::fabs(centerX) >= 0.95f || std::fabs(centerY) >= 0.95f)
            return {};

        // Keep original physical content aspect (not raw NDC ratio).
        // Shrink X and Y together into the clipped optical-centre margins;
        // do not independently clamp axes and stretch 4:3 menus at 21:9.
        const float usableHalfX = 1.0f - std::fabs(centerX);
        const float usableHalfY = 1.0f - std::fabs(centerY);
        const float halfWidth = (std::min)(
            usableHalfX, usableHalfY * requiredRatio);
        const float halfHeight = halfWidth / requiredRatio;
        if (!std::isfinite(halfWidth) || !std::isfinite(halfHeight) ||
            halfWidth < 0.05f || halfHeight < 0.05f)
            return {};

        return { true, centerX, centerY, halfWidth, halfHeight };
    }

    // The LOCAL menu samples the UV rectangle after desktop capture clipping.
    // A partially visible game window no longer occupies its GetClientRect()
    // width/height in the texture. Projecting that clipped UV with the full
    // window's aspect stretches it even when the common XR FOV is correct.
    // Derive the physical content aspect from the ACTUAL sampled pixels.
    // Fully visible windows yield the original client aspect. Reject a stale
    // or invalid capture publication without contaminating the menu geometry.
    inline float PlanCapturedAspect(
        std::uint32_t sourceWidth, std::uint32_t sourceHeight,
        float uvWidth, float uvHeight, float fallbackAspect) noexcept
    {
        if (!sourceWidth || !sourceHeight ||
            !std::isfinite(uvWidth) || !std::isfinite(uvHeight) ||
            uvWidth <= 0.0f || uvWidth > 1.0f ||
            uvHeight <= 0.0f || uvHeight > 1.0f)
            return fallbackAspect;

        const double sampledWidth =
            static_cast<double>(sourceWidth) * uvWidth;
        const double sampledHeight =
            static_cast<double>(sourceHeight) * uvHeight;
        const double aspect = sampledWidth / sampledHeight;
        if (!std::isfinite(aspect) || aspect < 0.5 || aspect > 5.0)
            return fallbackAspect;
        return static_cast<float>(aspect);
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
