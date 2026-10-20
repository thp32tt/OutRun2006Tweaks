#pragma once
// R26 gameplay HUD only: a 1920x1080 physical presentation reference.
// Original OutRun 640x480 logical sprite coordinates and native UIScaling
// remain untouched. No 1080p GPU render-target allocation is implied.
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace OutRunVRHud1080p
{
    constexpr std::uint32_t ReferenceWidth = 1920u;
    constexpr std::uint32_t ReferenceHeight = 1080u;
    constexpr float ReferenceAspect =
        static_cast<float>(ReferenceWidth) /
        static_cast<float>(ReferenceHeight);

    // Fit the gameplay HUD into the centered 16:9 viewing region when the
    // actual GAME backbuffer is wider than 1080p. Apply the SAME factor to
    // X/Y: UI circles remain round and the native source coordinates live.
    // Never use the portrait-shaped per-eye OpenXR texture as the game canvas.
    constexpr float ContainedScale(
        std::uint32_t gameWidth, std::uint32_t gameHeight) noexcept
    {
        if (!gameWidth || !gameHeight)
            return 1.0f;
        const float sourceAspect =
            static_cast<float>(gameWidth) /
            static_cast<float>(gameHeight);
        const float fit = ReferenceAspect / sourceAspect;
        return fit < 0.50f ? 0.50f : (fit > 1.0f ? 1.0f : fit);
    }

    inline float PlaneViewZ(float userDistance) noexcept
    {
        const float safe = std::isfinite(userDistance)
            ? std::clamp(userDistance, 2.50f, 8.0f) : 4.0f;
        return -safe;
    }

    static_assert(ReferenceWidth == 1920u && ReferenceHeight == 1080u);
    static_assert(ContainedScale(1920u, 1080u) == 1.0f);
    static_assert(ContainedScale(640u, 480u) == 1.0f);
    static_assert(ContainedScale(3440u, 1440u) < 0.75f);
    static_assert(ContainedScale(3440u, 1440u) > 0.74f);
    static_assert(ContainedScale(2496u, 2688u) == 1.0f);
}
