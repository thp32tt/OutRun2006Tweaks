#pragma once
// F11-only layout budget for a dynamic Quest3/XR mirror. Unlike the game HUD,
// this external ImGui window can shrink while its eye-density atlas is still
// large. Fit BOTH glyph metrics and control spacing to the capped shell;
// never affect native desktop settings or persist a changed user font scale.
#include <algorithm>
#include <cmath>

namespace OutRunF11ResponsiveFit
{
    struct Budget
    {
        float fontScale = 1.0f;
        float styleDensity = 1.0f;
    };


    // Observe the actual ImGui window after Begin, and clamp an escaped VR
    // drag/resize BEFORE the next Begin. This keeps drawing and hitboxes aligned.
    struct WindowRect { float x=0.f, y=0.f, width=0.f, height=0.f; };
    struct WindowCorrection
    {
        WindowRect rect{};
        bool valid=false, moved=false, resized=false;
    };
    inline WindowCorrection ContainWindow(const WindowRect& viewport,
        const WindowRect& observed, float maxWidth, float maxHeight) noexcept
    {
        const auto finiteRect = [](const WindowRect& r) noexcept {
            return std::isfinite(r.x) && std::isfinite(r.y) &&
                std::isfinite(r.width) && std::isfinite(r.height) &&
                r.width > 0.0f && r.height > 0.0f;
        };
        if (!finiteRect(viewport) || !finiteRect(observed) ||
            !std::isfinite(maxWidth) || !std::isfinite(maxHeight) ||
            maxWidth <= 0.f || maxHeight <= 0.f)
            return {};
        const float width = (std::min)(observed.width,
            (std::min)(viewport.width, maxWidth));
        const float height = (std::min)(observed.height,
            (std::min)(viewport.height, maxHeight));
        const float maxX = viewport.x + viewport.width - width;
        const float maxY = viewport.y + viewport.height - height;
        if (!std::isfinite(maxX) || !std::isfinite(maxY))
            return {};
        const float x = std::clamp(observed.x, viewport.x, maxX);
        const float y = std::clamp(observed.y, viewport.y, maxY);
        return {{x,y,width,height}, true,
            x != observed.x || y != observed.y,
            width != observed.width || height != observed.height};
    }

    inline Budget Compute(float availableWidth, float availableHeight,
        float requestedDensity) noexcept
    {
        if (!std::isfinite(availableWidth) || !std::isfinite(availableHeight) ||
            !std::isfinite(requestedDensity) ||
            availableWidth <= 0.0f || availableHeight <= 0.0f ||
            requestedDensity <= 0.0f)
            return {};

        // The font atlas remains rasterised once at source/eye density.
        // SetWindowFontScale reduces only the *window's* displayed glyph size;
        // no font rebuild, bitmap upscaling or global IO scale change.
        const float density = std::clamp(requestedDensity, 0.25f, 7.5f);
        // The shell tab body already scrolls; fitting glyphs against the full
        // 600px content height downscales the entire high-resolution XR font
        // before that scrollbar can be used. Reserve 480px for readable
        // tabs/controls and allow the existing child to scroll long settings.
        // The outer window stays capped by its actual viewport bounds.
        const float desiredWidth = 1130.0f * density;
        const float desiredHeight = 480.0f * density;
        const float rawFit = (std::min)(1.0f, (std::min)(
            availableWidth / desiredWidth, availableHeight / desiredHeight));
        // A nearly minimized/zero-area output cannot make interactive UI,
        // but ImGui must still have a strictly positive finite font scale.
        const float fontFit = std::clamp(rawFit, 0.25f, 1.0f);
        return { fontFit, std::clamp(density * fontFit, 0.25f, 3.0f) };
    }
}
