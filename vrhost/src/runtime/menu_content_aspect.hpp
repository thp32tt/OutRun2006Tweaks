#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
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

    // Configured 4:3 letterboxing is NOT evidence that the captured window's
    // side regions are empty. Quest3 A/B showed authored car-selection
    // geometry and a vehicle list beyond the nominal 4:3 centre. Cropping
    // those pixels based on an INI flag loses real content. Only enable the
    // automatic centre crop after independent image/matte verification.
    // The separate explicit user A/B override remains available.
    constexpr bool ShouldAutoCropVerifiedFourThree(
        bool configuredLetterbox, bool imageMatteVerified) noexcept
    {
        return configuredLetterbox && imageMatteVerified;
    }

    // Quest3 A/B: the whole Ferrari/list selector spans the captured 16:9
    // or 21:9 client. A title-oriented manual 4:3 crop must never carry
    // into selector/exit/reset (or an unknown transition) and truncate the
    // right-side options. Default remains no crop until source matte is
    // independently verified, with explicit title/menu A/B opt-in only.
    constexpr bool IsWideVehicleSelector(std::uint32_t state) noexcept
    {
        return state == 0x0Au || state == 0x0Bu || state == 0x0Cu;
    }

    constexpr bool PlanStateSafeMenuCrop(
        std::uint32_t state, bool configuredLetterbox,
        bool imageMatteVerified, bool requestedCrop,
        bool requestedNoCrop) noexcept
    {
        if (IsWideVehicleSelector(state) || requestedNoCrop)
            return false;
        // Unknown, gameplay and transition states cannot prove a 4:3
        // authored matte, even if the previous title enabled A/B cropping.
        if (state != 0x04u && state != 0x09u)
            return false;
        return requestedCrop ||
            ShouldAutoCropVerifiedFourThree(
                configuredLetterbox, imageMatteVerified);
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
    // A shared menu projection must intersect both eye frusta: averaging
    // their tangent-space edges can clip pixels in one physical eye.
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
        // Both published eyes must describe finite, physically bounded
        // tangent rectangles. A transient near-pole eye can be below the
        // angle guard (1.55 rad) yet span tens of tangent units, distorting
        // the *shared* optical menu for both eyes during recenter/Reset.
        // Fail closed before averaging: do not let one invalid eye drag the
        // other eye's centered menu or 4:3 aspect out of its authored plane.
        const float spanX0 = r0 - l0, spanX1 = r1 - l1;
        const float spanY0 = u0 - d0, spanY1 = u1 - d1;
        if (!(spanX0 > 0.05f && spanX0 <= 10.0f &&
              spanX1 > 0.05f && spanX1 <= 10.0f &&
              spanY0 > 0.05f && spanY0 <= 10.0f &&
              spanY1 > 0.05f && spanY1 <= 10.0f))
            return {};

        // Both OpenXR eyes display ONE common LOCAL-fixed menu projection.
        // Mean tangent edges may extend beyond the true bounds of either eye,
        // clipping the car selector/menu despite a centered common NDC quad.
        // Intersect instead; disjoint or degenerate eye frusta fail closed.
        const float left = (std::max)(l0, l1);
        const float right = (std::min)(r0, r1);
        const float down = (std::max)(d0, d1);
        const float up = (std::min)(u0, u1);
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

    // The 0.78 HMD default protects users who found a full-FOV theater
    // excessive. Some VD Low/High captures have a separately smaller inner
    // 16:9 panel. Allow a bounded per-session A/B without changing the
    // eye FOV, native captured aspect, UV, game window or stereo world.
    // Malformed/nonfinite values fail to the proven default, never stretch.
    inline float ResolveMenuOpticalCoverage(
        const char* requested) noexcept
    {
        constexpr float defaultCoverage = 0.78f;
        if (!requested || !*requested)
            return defaultCoverage;
        char* end = nullptr;
        const float parsed = std::strtof(requested, &end);
        if (end == requested || !end || *end != '\0' ||
            !std::isfinite(parsed) || parsed < 0.50f || parsed > 1.0f)
            return defaultCoverage;
        return parsed;
    }

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

    // Quest3 user A/B: the title/main menu is authored for a 4:3 UI but
    // game UIScalingMode=1/2 may submit it over a complete 16:9/21:9 raster.
    // Its stretched text must be corrected in the optical projection WITHOUT
    // cropping source UV: an unverified matte is never a licence to discard
    // actual texture pixels. The selector and selector-exit/reset states use
    // authored wide car previews and the right-side vehicle list instead.
    // Original GameState values come from src/game.hpp, published through
    // SharedPose::reserved[ClientGameStateIndex]; do not alter the IPC ABI.
    inline float PlanStateSensitiveMenuAspect(
        float sampledAspect, float fullClientAspect, std::uint32_t gameState,
        bool gameConfiguredLetterbox, bool fullyCaptured,
        bool cropAlreadyApplied, bool useNativeAspect) noexcept
    {
        constexpr std::uint32_t Title = 0x04u;
        constexpr std::uint32_t Menu = 0x09u;
        constexpr float FourThree = 4.0f / 3.0f;
        if ((gameState != Title && gameState != Menu) ||
            !gameConfiguredLetterbox || !fullyCaptured ||
            cropAlreadyApplied || useNativeAspect ||
            !std::isfinite(sampledAspect) ||
            !std::isfinite(fullClientAspect) ||
            !(sampledAspect > FourThree + 0.01f && sampledAspect <= 5.0f) ||
            !(fullClientAspect > FourThree + 0.01f &&
              fullClientAspect <= 5.0f) ||
            std::fabs(sampledAspect - fullClientAspect) > 0.02f)
            return sampledAspect;
        // Projection aspect only: full UV including title/menu edge pixels
        // is preserved. Selector/vanilla/partial/unknown states fail closed.
        return FourThree;
    }

    // Quest3 menu/car-select: some original 4:3 OutRun UI is rasterized
    // over the ENTIRE ultrawide game client (including the car/model list).
    // Cropping to 4:3 loses those authored pixels; projecting the uncropped
    // capture at clientAspect makes its physical VR plane too wide.
    // Restore the original authored 4:3 PHYSICAL aspect only if the
    // captured side matte has been verified independently. An INI flag
    // describes the requested layout, not the actual captured pixels;
    // forcing 4:3 for an uncropped 16:9/21:9 frame squeezes full-width
    // menu and vehicle-selection art into a second smaller theater.
    // A partially captured client cannot be squeezed as a whole because
    // its missing pixels must retain their old fragment/fallback handling.
    // No game HUD, stereo race, F11 or other desktop capture uses this plan.
    inline float PlanUncroppedAuthoredMenuAspect(
        float sampledAspect, float fullClientAspect,
        bool gameConfiguredLetterbox, bool fullyCaptured,
        bool cropAlreadyApplied, bool useNativeAspect,
        bool imageMatteVerified = false) noexcept
    {
        if (!gameConfiguredLetterbox || !imageMatteVerified ||
            !fullyCaptured || cropAlreadyApplied || useNativeAspect ||
            !std::isfinite(sampledAspect) ||
            !std::isfinite(fullClientAspect) ||
            sampledAspect < 0.5f || sampledAspect > 5.0f ||
            fullClientAspect < 0.5f || fullClientAspect > 5.0f)
            return sampledAspect;
        // Never manufacture an aspect correction for portrait/native 4:3:
        // those sources are already proportioned and must stay untouched.
        constexpr float authoredFourThree = 4.0f / 3.0f;
        return fullClientAspect > authoredFourThree + 0.01f
            ? authoredFourThree : sampledAspect;
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
