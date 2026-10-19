#pragma once
// The Sumo game uses logical 640x480 sprite positions. The output is the
// chosen D3D9Ex game source (same for gameplay and title/ESC menus).
// OpenXR eye extent and optical projection are intentionally NOT inputs.
// This is pure geometry, independent of device pointers, game state, and HMD.
#include <cmath>

namespace OutRunVR::LogicalUI
{
    struct Viewport
    {
        float scale{}, x{}, y{}, width{}, height{};
        bool valid = false;
    };
    inline Viewport Contain(
        float renderWidth, float renderHeight,
        float logicalWidth = 640.0f,
        float logicalHeight = 480.0f) noexcept
    {
        if (!std::isfinite(renderWidth) || !std::isfinite(renderHeight) ||
            !std::isfinite(logicalWidth) || !std::isfinite(logicalHeight) ||
            renderWidth <= 0.0f || renderHeight <= 0.0f ||
            logicalWidth <= 0.0f || logicalHeight <= 0.0f)
            return {};
        const float sx = renderWidth / logicalWidth;
        const float sy = renderHeight / logicalHeight;
        const float scale = sx < sy ? sx : sy;
        if (!std::isfinite(scale) || scale <= 0.0f)
            return {};
        const float width = logicalWidth * scale;
        const float height = logicalHeight * scale;
        const float x = (renderWidth - width) * 0.5f;
        const float y = (renderHeight - height) * 0.5f;
        if (!std::isfinite(width) || !std::isfinite(height) ||
            !std::isfinite(x) || !std::isfinite(y))
            return {};
        return {scale, x, y, width, height, true};
    }
    inline float MapX(const Viewport& v, float x) noexcept
    { return v.x + x * v.scale; }
    inline float MapY(const Viewport& v, float y) noexcept
    { return v.y + y * v.scale; }
}
