#pragma once
#include <cmath>

// Only the original OutRun ESC/pause shell and its exact arrow sprites opt in.
// Shared head-forward tangent centre corrects vertical XR FOV asymmetry; both
// eyes fall back to the original neutral transform on invalid publications.
namespace OutRunVrPauseEye
{
    // Source identity is supplied by CurrentRenderProducerToken: an active
    // SpriteNode wins over nested direct calls. Only exact ScreenHud arrows
    // may share the paused ESC shell's per-eye optical placement.
    constexpr bool ExactArrowOwner(bool screenHud, bool exactProducer) noexcept
    {
        return screenHud && exactProducer;
    }

    // The original ESC arrow E8 caller is a source identity, not the current
    // pause game-state alone. Reentrant native calls can change VR or mode
    // before registering SpriteNodes. Fail closed for the WHOLE queued batch;
    // generic screen clips retain their unmodified original owner.
    constexpr bool CanTagNativePauseArrow(bool vrEntry, bool vrExit,
        bool pauseEntry, bool pauseExit) noexcept
    {
        return vrEntry && vrExit && pauseEntry && pauseExit;
    }
    static_assert(CanTagNativePauseArrow(true, true, true, true));
    static_assert(!CanTagNativePauseArrow(true, false, true, true));
    static_assert(!CanTagNativePauseArrow(true, true, true, false));
    static_assert(!CanTagNativePauseArrow(false, true, true, true));
    static_assert(!CanTagNativePauseArrow(true, true, false, true));

    // Exact PauseFrameDisp subtree only. A pause game-state bit plus a generic
    // ScreenOverlay2D queue is not sufficient ownership: other queued 2D
    // content can coexist while paused and must keep its ordinary HUD policy.
    constexpr bool ExactShellOwner(bool screenOverlay, bool exactProducer) noexcept
    {
        return screenOverlay && exactProducer;
    }
    static_assert(ExactShellOwner(true, true));
    static_assert(!ExactShellOwner(true, false));
    static_assert(!ExactShellOwner(false, true));

    // R84 native ESC producer -> queued child text -> shader GPU sink.
    // The caller has already established exact ScreenHud or a live
    // same-node/epoch ScreenOverlay2D WVP. Pause state is mandatory in BOTH
    // cases; unrelated menus, F11, world and +TIME never inherit the slider.
    constexpr bool OwnsPauseShaderPlane(
        bool sourceHud, bool sourceQueuedOverlay, bool originalPause) noexcept
    {
        return originalPause && (sourceHud || sourceQueuedOverlay);
    }
    static_assert(OwnsPauseShaderPlane(true, false, true));
    static_assert(OwnsPauseShaderPlane(false, true, true));
    static_assert(!OwnsPauseShaderPlane(false, false, true));
    static_assert(!OwnsPauseShaderPlane(false, true, false));
    static_assert(!OwnsPauseShaderPlane(true, false, false));

    struct VerticalAffine
    {
        float scale[2]{1.0f, 1.0f};
        float offset[2]{0.0f, 0.0f};
        bool valid = false;
    };

    // The legacy 1.0 setting corresponded to a 1.25 optical floor, making
    // 0.55..1.24 completely unresponsive in portrait XR mode. Preserve that
    // readable default while granting the full slider a monotone mapping.
    // Nonresponsive desktop/legacy configurations retain the exact request.
    inline float ResponsiveUserScale(float requested, bool responsive) noexcept
    {
        if (!responsive || !std::isfinite(requested) || requested <= 0.0f)
            return requested;
        const float bounded = requested < 0.55f ? 0.55f :
            (requested > 1.50f ? 1.50f : requested);
        return bounded <= 1.0f
            ? 0.55f + (bounded - 0.55f) * (0.70f / 0.45f)
            : 1.25f + (bounded - 1.0f) * 0.50f;
    }

    // The original pause shell occupies only a narrow central portion of
    // the widescreen source. A portrait XR eye needs a larger optical scale
    // after aspect-preserving containment; otherwise the menu remains tiny
    // even at PauseMenuScale=1.25. Do not stretch X and Y independently.
    // Caller authorizes only the exact original ESC/pause producer, and the
    // normal desktop/legacy paths must remain bit-identical.
    inline float ResponsiveMenuScale(
        float menuScale, float sourceOverEyeAspect, bool responsive) noexcept
    {
        if (!responsive || !std::isfinite(menuScale) || menuScale <= 0.0f ||
            !std::isfinite(sourceOverEyeAspect) ||
            sourceOverEyeAspect <= 1.0f)
            return menuScale;
        // Preserve the original aspect compensation while offsetting the
        // portrait containment shrink by its geometric mean. The 2.25 cap
        // also protects the pause option arrows from huge malformed extents.
        const float boundedAspect =
            sourceOverEyeAspect < 3.50f ? sourceOverEyeAspect : 3.50f;
        const float boosted = menuScale * std::sqrt(boundedAspect);
        if (!std::isfinite(boosted))
            return menuScale;
        // Smoothly reserve the last 0.30x of the safe optical budget.
        // A hard clamp made the larger slider positions indistinguishable;
        // the rational shoulder remains strictly increasing below 2.25x.
        constexpr float shoulder = 1.95f;
        constexpr float headroom = 0.30f;
        if (boosted <= shoulder)
            return boosted;
        const float excess = boosted - shoulder;
        return shoulder + headroom * excess / (headroom + excess);
    }

    // Shader-backed ESC shell must share the same horizontal per-eye FOV
    // dilation as the XYZRHW arrows. Keep legacy gameplay HUD and F11
    // shader transforms untouched; this is an exact pause-state opt-in.
    inline float ShaderHorizontalScale(
        float commonScale, float eyeFovScale, bool pauseOwned) noexcept
    {
        return pauseOwned ? commonScale * eyeFovScale : commonScale;
    }

    // R84 pause shell and exact shader-owned option arrows originate in
    // native game pixels, whereas each headset eye has its own pixel aspect.
    // Both submission paths must use ONE contained optical size. This is
    // not a general HUD/F11 or world-billboard transform.
    struct AspectContainedScale
    {
        float x = 1.0f;
        float y = 1.0f;
    };

    inline AspectContainedScale ContainNativePauseScale(
        float userScale, float sourceOverTarget, bool pauseResponsive) noexcept
    {
        if (!pauseResponsive || !std::isfinite(userScale) ||
            userScale <= 0.0f || !std::isfinite(sourceOverTarget) ||
            sourceOverTarget <= 0.0f)
            return {userScale, userScale};
        if (sourceOverTarget >= 1.0f)
            return {userScale, userScale / sourceOverTarget};
        return {userScale * sourceOverTarget, userScale};
    }

    inline VerticalAffine Compute(
        float leftDown, float leftUp, float rightDown, float rightUp) noexcept
    {
        const float downs[2]{leftDown, rightDown};
        const float ups[2]{leftUp, rightUp};
        float span[2]{}, sum[2]{};
        for (int eye = 0; eye < 2; ++eye)
        {
            if (!std::isfinite(downs[eye]) || !std::isfinite(ups[eye]) ||
                downs[eye] >= ups[eye])
                return {};
            const float tDown = std::tan(downs[eye]);
            const float tUp = std::tan(ups[eye]);
            span[eye] = tUp - tDown;
            sum[eye] = tUp + tDown;
            if (!std::isfinite(span[eye]) || !std::isfinite(sum[eye]) ||
                span[eye] <= 0.05f || span[eye] > 10.0f)
                return {};
        }
        const float common = 0.5f * (span[0] + span[1]);
        VerticalAffine result{};
        for (int eye = 0; eye < 2; ++eye)
        {
            const float s = common / span[eye];
            const float o = -sum[eye] / span[eye];
            if (!std::isfinite(s) || !std::isfinite(o) ||
                s < 0.50f || s > 1.50f || std::fabs(o) > 0.50f)
                return {};
            result.scale[eye] = s;
            result.offset[eye] = o;
        }
        result.valid = true;
        return result;
    }
    // ESC's XYZRHW shell applies user vertical positioning AFTER
    // perspective/eye mapping. Its shader-backed arrows must use the same
    // screen-space operation: clipY += shift * clipW. Moving a HUD plane in
    // game space before head/eye projection makes it drift when the HMD
    // rotates or asymmetric per-eye FOV changes. Preserve every matrix field
    // except clip Y coefficients and fail neutral for invalid settings.
    template <class Matrix>
    inline Matrix ApplyPostProjectionVerticalShift(
        const Matrix& projected, float ndcShift) noexcept
    {
        if (!std::isfinite(ndcShift) || ndcShift == 0.0f)
            return projected;
        Matrix aligned = projected;
        aligned._12 += ndcShift * projected._14;
        aligned._22 += ndcShift * projected._24;
        aligned._32 += ndcShift * projected._34;
        aligned._42 += ndcShift * projected._44;
        return aligned;
    }

}
