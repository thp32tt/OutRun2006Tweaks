#pragma once

#include "../render/draw_class.hpp"

#include <cstdint>

namespace OutRunVR::Core
{
    // Stable routing vocabulary for the future single D3D9 hook dispatcher.
    // This is policy-only in the current refactor stage: live R-series hooks
    // continue to own rendering until each route is migrated and validated.
    enum class DispatchRoute : std::uint8_t
    {
        LegacyFailClosed = 0,
        WorldStereo,
        ScreenHud,
        ScreenOverlay2D,
        WorldBillboard,
        SkyGlow,
        FragileEffect,
        Auxiliary,
        ZeroDisparity,
    };

    constexpr DispatchRoute RouteFor(Render::DrawClass drawClass) noexcept
    {
        switch (drawClass)
        {
        case Render::DrawClass::World:
            return DispatchRoute::WorldStereo;
        case Render::DrawClass::ScreenHud:
            return DispatchRoute::ScreenHud;
        case Render::DrawClass::ScreenOverlay2D:
            return DispatchRoute::ScreenOverlay2D;
        case Render::DrawClass::WorldBillboard:
            return DispatchRoute::WorldBillboard;
        case Render::DrawClass::SkyGlow:
            return DispatchRoute::SkyGlow;
        case Render::DrawClass::FragileEffect:
            return DispatchRoute::FragileEffect;
        case Render::DrawClass::Auxiliary:
            return DispatchRoute::Auxiliary;
        case Render::DrawClass::ZeroDisparity:
            return DispatchRoute::ZeroDisparity;
        default:
            return DispatchRoute::LegacyFailClosed;
        }
    }

    constexpr bool IsSpatialRoute(DispatchRoute route) noexcept
    {
        return route == DispatchRoute::WorldStereo ||
            route == DispatchRoute::WorldBillboard;
    }

    constexpr bool IsScreenRoute(DispatchRoute route) noexcept
    {
        return route == DispatchRoute::ScreenHud ||
            route == DispatchRoute::ScreenOverlay2D;
    }

    static_assert(RouteFor(Render::DrawClass::World) ==
        DispatchRoute::WorldStereo);
    static_assert(RouteFor(Render::DrawClass::ScreenHud) ==
        DispatchRoute::ScreenHud);
    static_assert(RouteFor(Render::DrawClass::WorldBillboard) ==
        DispatchRoute::WorldBillboard);
    static_assert(RouteFor(Render::DrawClass::Unknown) ==
        DispatchRoute::LegacyFailClosed);
    static_assert(IsSpatialRoute(DispatchRoute::WorldStereo));
    static_assert(!IsSpatialRoute(DispatchRoute::ScreenHud));
}
