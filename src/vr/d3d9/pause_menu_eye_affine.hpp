#pragma once
#include <cmath>

// Only the original OutRun ESC/pause shell and its exact arrow sprites opt in.
// Shared head-forward tangent centre corrects vertical XR FOV asymmetry; both
// eyes fall back to the original neutral transform on invalid publications.
namespace OutRunVrPauseEye
{
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
}
