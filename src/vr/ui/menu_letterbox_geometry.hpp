#pragma once
#include <array>
#include <cstdint>

namespace OutRunVR::UI
{
    // The original menu is authored in a 4:3 coordinate space. Widescreen
    // mirrors need side rails; square/portrait XR sources need TOP/BOTTOM
    // rails, not the widescreen-only early return in the original overlay.
    enum class MenuBarAxis : std::uint8_t { Invalid, None, Sides, TopBottom };
    struct MenuBarPoint { float x, y; };
    struct MenuBarGeometry
    {
        MenuBarAxis axis = MenuBarAxis::Invalid;
        std::array<MenuBarPoint, 8> vertices{};
        constexpr bool hasBars() const noexcept
        {
            return axis == MenuBarAxis::Sides ||
                   axis == MenuBarAxis::TopBottom;
        }
    };

    constexpr MenuBarGeometry BuildMenuBarGeometry(
        float sourceWidth, float sourceHeight) noexcept
    {
        // Bounded, finite D3D9 source dimensions. NaN fails these relational
        // checks, and +infinity fails the maximum bound.
        if (!(sourceWidth >= 1.0f && sourceWidth <= 16384.0f &&
              sourceHeight >= 1.0f && sourceHeight <= 16384.0f))
            return {};

        const float containWidth = sourceHeight * (4.0f / 3.0f);
        const float containHeight = sourceWidth * (3.0f / 4.0f);
        const float right = sourceWidth + 0.5f;
        const float bottom = sourceHeight + 0.5f;
        MenuBarGeometry result{};
        if (sourceWidth > containWidth + 0.5f)
        {
            const float edge = (sourceWidth - containWidth) * 0.5f + 0.5f;
            result.axis = MenuBarAxis::Sides;
            result.vertices = {{
                {-0.5f, -0.5f}, {edge, -0.5f},
                {-0.5f, bottom}, {edge, bottom},
                {right - edge, -0.5f}, {right, -0.5f},
                {right - edge, bottom}, {right, bottom}
            }};
        }
        else if (sourceHeight > containHeight + 0.5f)
        {
            const float edge = (sourceHeight - containHeight) * 0.5f + 0.5f;
            result.axis = MenuBarAxis::TopBottom;
            result.vertices = {{
                {-0.5f, -0.5f}, {right, -0.5f},
                {-0.5f, edge}, {right, edge},
                {-0.5f, bottom - edge}, {right, bottom - edge},
                {-0.5f, bottom}, {right, bottom}
            }};
        }
        else
        {
            result.axis = MenuBarAxis::None;
        }
        return result;
    }


    // F11's frontend shell must occupy exactly the uncovered menu pixels.
    // Reuse the same geometry as the GPU side/top-bottom black strips, rather
    // than independently assuming every output is landscape.
    struct MenuContentBounds
    {
        float x = 0.0f, y = 0.0f, width = 0.0f, height = 0.0f;
        constexpr bool valid() const noexcept
        {
            return width > 0.0f && height > 0.0f;
        }
    };

    constexpr MenuContentBounds BuildMenuContentBounds(
        float sourceWidth, float sourceHeight) noexcept
    {
        const auto bars = BuildMenuBarGeometry(sourceWidth, sourceHeight);
        if (bars.axis == MenuBarAxis::Invalid)
            return {};
        if (bars.axis == MenuBarAxis::Sides)
        {
            const float left = bars.vertices[1].x;
            const float right = bars.vertices[4].x;
            return { left, 0.0f, right - left, sourceHeight };
        }
        if (bars.axis == MenuBarAxis::TopBottom)
        {
            const float top = bars.vertices[2].y;
            const float bottom = bars.vertices[4].y;
            return { 0.0f, top, sourceWidth, bottom - top };
        }
        return { 0.0f, 0.0f, sourceWidth, sourceHeight };
    }

    static_assert(BuildMenuContentBounds(640, 480).width == 640.0f);
    static_assert(BuildMenuContentBounds(1920, 1080).x == 240.5f);
    static_assert(BuildMenuContentBounds(1920, 1080).width == 1439.5f);
    static_assert(BuildMenuContentBounds(1200, 1600).x == 0.0f);
    static_assert(BuildMenuContentBounds(1200, 1600).y == 350.5f);
    static_assert(BuildMenuContentBounds(1200, 1600).height == 899.5f);
    static_assert(!BuildMenuContentBounds(0, 1600).valid());
    static_assert(!BuildMenuContentBounds(16385, 1600).valid());

    // Compile as part of the real x86 game binary: native, widescreen,
    // ultrawide and XR portrait must retain distinct, bounded bar geometry.
    static_assert(BuildMenuBarGeometry(640, 480).axis == MenuBarAxis::None);
    static_assert(BuildMenuBarGeometry(1920, 1080).axis == MenuBarAxis::Sides);
    static_assert(BuildMenuBarGeometry(3440, 1440).vertices[0].x == -0.5f);
    static_assert(BuildMenuBarGeometry(3440, 1440).vertices[1].x == 760.5f);
    static_assert(BuildMenuBarGeometry(1200, 1600).axis == MenuBarAxis::TopBottom);
    static_assert(BuildMenuBarGeometry(1200, 1600).vertices[2].y == 350.5f);
    static_assert(BuildMenuBarGeometry(1200, 1600).vertices[4].y == 1250.0f);
    static_assert(BuildMenuBarGeometry(1200, 1600).vertices[1].x == 1200.5f);
    static_assert(BuildMenuBarGeometry(1200, 1600).vertices[7].y == 1600.5f);
    static_assert(BuildMenuBarGeometry(1200, 1600).hasBars());
    static_assert(!BuildMenuBarGeometry(640, 480).hasBars());
    static_assert(BuildMenuBarGeometry(0, 1000).axis == MenuBarAxis::Invalid);
    static_assert(BuildMenuBarGeometry(16385, 1000).axis == MenuBarAxis::Invalid);
    static_assert(BuildMenuBarGeometry(1200, 1600).vertices[2].y <
                  BuildMenuBarGeometry(1200, 1600).vertices[4].y);
}
