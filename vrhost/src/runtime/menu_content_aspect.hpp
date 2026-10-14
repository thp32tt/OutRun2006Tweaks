#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
// Opt-in center-content crop for the captured, already-letterboxed 4:3
// OutRun menu. The LOCAL-fixed two-eye clip must use the SAME resulting
// content aspect and UV, not the ultrawide desktop aspect with black rails.
namespace OutRunVrMenuAspect
{
    // Automatic 4:3 menu crop is valid only when the game itself is drawing
    // the 4:3 letterbox. Vanilla/stretched or unletterboxed menus must keep
    // the complete captured client. Environment overrides remain reversible.
    constexpr bool ShouldCropConfiguredMenu(int scalingMode,
        int letterboxingMode) noexcept
    {
        return scalingMode >= 1 && scalingMode <= 2 &&
            letterboxingMode >= 1 && letterboxingMode <= 2;
    }

    // OutRun may restart with a recycled numeric HWND but a new game PID.
    // A cached 4:3 crop must never be reused for another process.
    // Preserve the bounded INI polling interval within the same process.
    constexpr bool ShouldRefreshMenuLetterboxConfig(
        std::uintptr_t cachedWindow, std::uint32_t cachedPid,
        std::uint64_t nextCheckMs, std::uintptr_t observedWindow,
        std::uint32_t observedPid, std::uint64_t nowMs) noexcept
    {
        return observedWindow == 0 || observedPid == 0 ||
            cachedWindow != observedWindow || cachedPid != observedPid ||
            nowMs >= nextCheckMs;
    }

    struct CropPlan
    {
        bool crop = false;
        float offsetX = 0.0f;  // fraction of the captured game client width
        float width = 1.0f;
        float aspect = 0.0f;
        // Where the visible fragment belongs inside the ORIGINAL 4:3
        // menu, in fractions of the full authored half-extent. A window
        // clipped by Desktop Duplication must not zoom the surviving pixels
        // back to the optical centre or distort their physical proportions.
        float visibleOffsetX = 0.0f;
        float visibleOffsetY = 0.0f;  // positive means below authored centre
        float visibleWidthScale = 1.0f;
        float visibleHeightScale = 1.0f;
        // Source UV cropping is independent from optical fragment placement.
        float offsetY = 0.0f;
        float height = 1.0f;
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
        const CommonFovTangents& fov, float sourceAspect,
        float coverage = 1.0f) noexcept
    {
        if (!fov.valid || !std::isfinite(sourceAspect) ||
            sourceAspect < 0.5f || sourceAspect > 5.0f ||
            !std::isfinite(coverage) || coverage < 0.50f ||
            coverage > 1.0f ||
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
        // Shrink X and Y together into the clipped optical-centre margins.
        // A validated coverage below 1 keeps the old 4:3 theater from
        // occupying the full Quest field of view (no independent X/Y zoom).
        // do not independently clamp axes and stretch 4:3 menus at 21:9.
        const float usableHalfX = 1.0f - std::fabs(centerX);
        const float usableHalfY = 1.0f - std::fabs(centerY);
        const float halfWidth = (std::min)(
            usableHalfX, usableHalfY * requiredRatio) * coverage;
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
        // Horizontal sidebars on wide clients; vertical top/bottom matte
        // on portrait sources. Leave a native 4:3 client unchanged.
        if (!(sourceAspect >= 0.5f && sourceAspect <= 5.0f) ||
            !(intendedAspect >= 0.5f && intendedAspect <= 4.0f) ||
            sourceAspect == intendedAspect)
            return { false, 0.0f, 1.0f, sourceAspect };
        if (sourceAspect > intendedAspect)
        {
            const float width = intendedAspect / sourceAspect;
            return { true, (1.0f - width) * 0.5f, width, intendedAspect };
        }
        const float height = sourceAspect / intendedAspect;
        CropPlan plan{ true, 0.0f, 1.0f, intendedAspect };
        plan.offsetY = (1.0f - height) * 0.5f;
        plan.height = height;
        return plan;
    }

    // OutRun's authored 4:3 sidebars belong to the FULL game client, not
    // the portion of the window still visible on a desktop output. If a
    // window straddles the output edge, cropping a centred fraction of the
    // already-clipped UV recentres the WRONG pixels (or skips the crop).
    // Intersect the original client-space 4:3 content with the sampled UV
    // instead. Return fractions relative to the CURRENT sampled region so
    // both eyes use the identical, actually visible crop.
    inline CropPlan PlanVisibleCenteredContent(
        float clientLeft, float clientTop,
        float clientRight, float clientBottom,
        float captureWidth, float captureHeight,
        float uvX, float uvY, float uvWidth, float uvHeight,
        float intendedAspect) noexcept
    {
        const float values[]{
            clientLeft, clientTop, clientRight, clientBottom,
            captureWidth, captureHeight, uvX, uvY, uvWidth, uvHeight,
            intendedAspect
        };
        for (const float value : values)
            if (!std::isfinite(value))
                return {};

        const float clientWidth = clientRight - clientLeft;
        const float clientHeight = clientBottom - clientTop;
        if (!(clientWidth > 0.0f && clientHeight > 0.0f) ||
            !(captureWidth > 0.0f && captureHeight > 0.0f) ||
            !(uvX >= 0.0f && uvY >= 0.0f &&
              uvWidth > 0.0f && uvHeight > 0.0f) ||
            uvX + uvWidth > 1.00001f ||
            uvY + uvHeight > 1.00001f)
            return {};

        const float originalAspect = clientWidth / clientHeight;
        const auto fullPlan = PlanCenteredContent(
            originalAspect, intendedAspect);
        // Native 4:3 has no matte to remove. A PARTIALLY captured native
        // menu still needs its original optical placement: otherwise the
        // surviving fragment is incorrectly expanded and recentered on the
        // Quest menu quad. Do not accept an invalid/mismatched target aspect.
        if (!fullPlan.crop &&
            (!(originalAspect >= 0.5f && originalAspect <= 5.0f) ||
             !(intendedAspect >= 0.5f && intendedAspect <= 4.0f) ||
             std::fabs(originalAspect - intendedAspect) > 0.0005f))
            return {};

        const float sampledLeft = uvX * captureWidth;
        const float sampledRight = (uvX + uvWidth) * captureWidth;
        const float sampledTop = uvY * captureHeight;
        const float sampledBottom = (uvY + uvHeight) * captureHeight;
        // The UV must describe the actual client/output intersection.
        // A stale frame after moving outputs or Reset cannot be recropped.
        if (std::fabs(sampledLeft -
                (std::max)(0.0f, clientLeft)) > 1.0f ||
            std::fabs(sampledRight -
                (std::min)(captureWidth, clientRight)) > 1.0f ||
            std::fabs(sampledTop -
                (std::max)(0.0f, clientTop)) > 1.0f ||
            std::fabs(sampledBottom -
                (std::min)(captureHeight, clientBottom)) > 1.0f)
            return {};

        // A completely visible native 4:3 client needs no UV crop or
        // optical placement override. Only a genuinely clipped fragment
        // should opt in. After a window move/Reset the full image restores
        // the default path without retaining a stale fragment transform.
        if (!fullPlan.crop &&
            std::fabs(sampledLeft - clientLeft) <= 1.0f &&
            std::fabs(sampledRight - clientRight) <= 1.0f &&
            std::fabs(sampledTop - clientTop) <= 1.0f &&
            std::fabs(sampledBottom - clientBottom) <= 1.0f)
            return {};

        // Intersect the ORIGINAL authored 4:3 rectangle with the captured
        // client fragment. Portrait and landscape matte use different axes.
        const float contentWidth =
            (std::min)(clientWidth, clientHeight * intendedAspect);
        const float contentHeight = contentWidth / intendedAspect;
        const float contentLeft = clientLeft + (clientWidth - contentWidth) * 0.5f;
        const float contentTop = clientTop + (clientHeight - contentHeight) * 0.5f;
        const float contentRight = contentLeft + contentWidth;
        const float contentBottom = contentTop + contentHeight;
        const float visibleLeft = (std::max)(sampledLeft, contentLeft);
        const float visibleRight = (std::min)(sampledRight, contentRight);
        const float visibleTop = (std::max)(sampledTop, contentTop);
        const float visibleBottom = (std::min)(sampledBottom, contentBottom);
        const float visibleWidth = visibleRight - visibleLeft;
        const float visibleHeight = visibleBottom - visibleTop;
        const float sampledWidth = sampledRight - sampledLeft;
        const float sampledHeight = sampledBottom - sampledTop;
        if (!(visibleWidth > 0.0f && visibleHeight > 0.0f &&
              sampledWidth > 0.0f && sampledHeight > 0.0f &&
              contentWidth > 0.0f && contentHeight > 0.0f) ||
            visibleWidth < 0.05f * sampledWidth ||
            visibleHeight < 0.05f * sampledHeight)
            return {};

        const float visibleAspect = visibleWidth / visibleHeight;
        const float visibleOffsetX =
            (visibleLeft + visibleRight - contentLeft - contentRight) /
            contentWidth;
        const float visibleOffsetY =
            (visibleTop + visibleBottom - contentTop - contentBottom) /
            contentHeight;
        const float widthScale = visibleWidth / contentWidth;
        const float heightScale = visibleHeight / contentHeight;
        // The visible part may be a very thin but valid slice of the
        // original 4:3 menu. Limits for a FULL source aspect do not apply
        // to its clipped fragment: rejecting <0.5 or >5 here makes R23
        // project that surviving strip at the wrong full-menu size.
        // Physical slice size and position are instead recovered from the
        // original content rectangle, with a nonzero finite aspect.
        if (!std::isfinite(visibleAspect) || visibleAspect <= 0.0f ||
            !std::isfinite(visibleOffsetX) ||
            !std::isfinite(visibleOffsetY) ||
            !(widthScale > 0.0f && widthScale <= 1.00001f) ||
            !(heightScale > 0.0f && heightScale <= 1.00001f))
            return {};
        CropPlan result{ true, (visibleLeft - sampledLeft) / sampledWidth,
            visibleWidth / sampledWidth, visibleAspect,
            visibleOffsetX, visibleOffsetY, widthScale, heightScale };
        result.offsetY = (visibleTop - sampledTop) / sampledHeight;
        result.height = visibleHeight / sampledHeight;
        return result;
    }

    // LOCAL mono theater fallback (including a recovered menu) may sample a
    // clipped desktop window. GetGameUv() contains only the surviving pixels;
    // assigning those pixels the old FULL client quad zooms/recenters them.
    // Keep a full-size original client coordinate plane and render its actual
    // captured fragment in that plane. SBS has a different centre seam and
    // deliberately does not use this mono-only plan.
    struct MonoTheaterFragment
    {
        bool valid = false;
        bool partial = false;
        float quadWidth = 2.0f;
        float quadHeight = 0.0f;
        float offsetRight = 0.0f;
        float offsetUp = 0.0f;
    };

    inline MonoTheaterFragment PlanVisibleMonoTheaterFragment(
        float clientLeft, float clientTop,
        float clientRight, float clientBottom,
        float captureWidth, float captureHeight,
        float uvX, float uvY, float uvWidth, float uvHeight) noexcept
    {
        const float inputs[]{
            clientLeft, clientTop, clientRight, clientBottom,
            captureWidth, captureHeight, uvX, uvY, uvWidth, uvHeight
        };
        for (float v : inputs)
            if (!std::isfinite(v))
                return {};

        const float width = clientRight - clientLeft;
        const float height = clientBottom - clientTop;
        if (!(width > 0.0f && height > 0.0f &&
              captureWidth > 0.0f && captureHeight > 0.0f &&
              uvX >= 0.0f && uvY >= 0.0f &&
              uvWidth > 0.0f && uvHeight > 0.0f &&
              uvX + uvWidth <= 1.00001f &&
              uvY + uvHeight <= 1.00001f) ||
            width / height < 0.5f || width / height > 5.0f)
            return {};

        const float left = (std::max)(0.0f, clientLeft);
        const float right = (std::min)(captureWidth, clientRight);
        const float top = (std::max)(0.0f, clientTop);
        const float bottom = (std::min)(captureHeight, clientBottom);
        if (!(right > left && bottom > top))
            return {};

        // Require the CURRENT captured UV to describe the original
        // client/output intersection; reject stale capture after a
        // move, Reset or output switch. Use the same one-pixel tolerance as
        // the world-locked menu crop.
        if (std::fabs(uvX * captureWidth - left) > 1.0f ||
            std::fabs((uvX + uvWidth) * captureWidth - right) > 1.0f ||
            std::fabs(uvY * captureHeight - top) > 1.0f ||
            std::fabs((uvY + uvHeight) * captureHeight - bottom) > 1.0f)
            return {};

        MonoTheaterFragment result{};
        result.valid = true;
        result.partial =
            std::fabs(left - clientLeft) > 1.0f ||
            std::fabs(right - clientRight) > 1.0f ||
            std::fabs(top - clientTop) > 1.0f ||
            std::fabs(bottom - clientBottom) > 1.0f;
        // The original authored theater has width 2 and height
        // 2*clientHeight/clientWidth. Scale BOTH axes by the same physical
        // pixel density, but retain the captured rectangle's true centre.
        result.quadWidth = 2.0f * (right - left) / width;
        result.quadHeight = 2.0f * (bottom - top) / width;
        result.offsetRight =
            (left + right - clientLeft - clientRight) / width;
        result.offsetUp =
            -(top + bottom - clientTop - clientBottom) / width;
        if (!std::isfinite(result.quadWidth) ||
            !std::isfinite(result.quadHeight) ||
            !std::isfinite(result.offsetRight) ||
            !std::isfinite(result.offsetUp) ||
            result.quadWidth <= 0.0f || result.quadWidth > 2.00001f ||
            result.quadHeight <= 0.0f || result.quadHeight > 4.00001f)
            return {};
        return result;
    }

}
