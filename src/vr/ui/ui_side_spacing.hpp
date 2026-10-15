#pragma once
// Pixel width left on EACH side after fitting a game's authored 4:3 UI
// within the current target. On portrait/near-square XR eyes the width,
// rather than the height, is the limiting axis, so horizontal padding is 0.
// This is only for the original OnlineArcade-side producer offsets; other
// gameplay/world/menu containment remains owned by its existing paths.
namespace OutRunVrUiAspect
{
    constexpr float ContainedSidePaddingPixels(float targetWidth,
        float originalWidth, float screenScaleX, float screenScaleY) noexcept
    {
        if (!(targetWidth > 0.0f && originalWidth > 0.0f &&
              screenScaleX > 0.0f && screenScaleY > 0.0f))
            return 0.0f;
        const float contain =
            screenScaleX < screenScaleY ? screenScaleX : screenScaleY;
        const float padding =
            (targetWidth - originalWidth * contain) * 0.5f;
        return padding > 0.0f ? padding : 0.0f;
    }

    // Regression for native 4:3, desktop 16:9 / 21:9 and Quest3 VDXR
    // narrow single-eye targets. No negative x-padding on portrait eyes.
    static_assert(ContainedSidePaddingPixels(1280.0f, 640.0f, 2.0f, 2.0f) == 0.0f);
    static_assert(ContainedSidePaddingPixels(1920.0f, 640.0f, 3.0f, 2.25f) == 240.0f);
    static_assert(ContainedSidePaddingPixels(3440.0f, 640.0f, 5.375f, 3.0f) == 760.0f);
    static_assert(ContainedSidePaddingPixels(2064.0f, 640.0f, 3.225f, 4.6f) == 0.0f);
    static_assert(ContainedSidePaddingPixels(2496.0f, 640.0f, 3.9f, 5.4f) == 0.0f);
}