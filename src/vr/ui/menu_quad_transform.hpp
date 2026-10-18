#pragma once
// Complete game custom-sprite quad mapping: all vertices use the same
// post-D3DX affine. Only Vanilla title/menu/selector is allowed an explicit
// anisotropic X stretch; original HUD/GOAL and unknown-mode paths are stable.
#include <cmath>

namespace OutRunVrMenuQuad
{
    struct PixelMap
    {
        float scaleX = 0.0f, scaleY = 0.0f;
        float offsetX = 0.0f, offsetY = 0.0f;
        bool valid = false;
    };

    inline PixelMap BuildPixelMap(bool contained, bool vanillaFrontEnd,
        float screenScaleX, float screenScaleY,
        float screenWidth, float screenHeight,
        float sourceWidth, float sourceHeight,
        bool physicalMenuFill = false) noexcept
    {
        if (!std::isfinite(screenScaleX) || !std::isfinite(screenScaleY) ||
            screenScaleX <= 0.0f || screenScaleY <= 0.0f)
            return {};
        if (!contained)
            return {vanillaFrontEnd ? screenScaleX : screenScaleY,
                    screenScaleY, 0.0f, 0.0f, true};
        if (!std::isfinite(screenWidth) || !std::isfinite(screenHeight) ||
            !std::isfinite(sourceWidth) || !std::isfinite(sourceHeight) ||
            screenWidth <= 0.0f || screenHeight <= 0.0f ||
            sourceWidth <= 0.0f || sourceHeight <= 0.0f)
            return {};
        // Containment is a physical output contract, not only the game's
        // cached screen_scale. During a size/reset transition screen_scale
        // can still describe the old backbuffer while the new source extent
        // is already published. Never let an authored menu/custom sprite
        // overflow the new viewport or crop the right car-selector artwork.
        // Respect deliberately smaller game scales; cap only oversize ones.
        const float physicalX = screenWidth / sourceWidth;
        const float physicalY = screenHeight / sourceHeight;
        if (!std::isfinite(physicalX) || !std::isfinite(physicalY) ||
            physicalX <= 0.0f || physicalY <= 0.0f)
            return {};
        const float gameScale = screenScaleX < screenScaleY
            ? screenScaleX : screenScaleY;
        const float physicalScale = physicalX < physicalY
            ? physicalX : physicalY;
        // Only the centered title/menu/selector opts into full 4:3
        // letterbox filling. Legacy gameplay/smaller-scale paths stay
        // explicitly bounded by the original game scale.
        const float scale = physicalMenuFill ? physicalScale :
            (gameScale < physicalScale ? gameScale : physicalScale);
        const float offsetX = (screenWidth - sourceWidth * scale) * 0.5f;
        const float offsetY = (screenHeight - sourceHeight * scale) * 0.5f;
        if (!std::isfinite(offsetX) || !std::isfinite(offsetY) ||
            !std::isfinite(scale) || scale <= 0.0f)
            return {};
        return {scale, scale, offsetX, offsetY, true};
    }

    inline float ProjectX(const PixelMap& m, float x) noexcept
    {
        return m.scaleX * x + m.offsetX + 0.5f;
    }
    inline float ProjectY(const PixelMap& m, float y) noexcept
    {
        return m.scaleY * y + m.offsetY + 0.5f;
    }
}
