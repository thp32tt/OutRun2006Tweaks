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
