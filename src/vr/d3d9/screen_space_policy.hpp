#pragma once

#include "vr/d3d9/render_policy.hpp"

#include <cstdint>

namespace OutRunVR::ScreenSpacePolicy
{
    enum class Kind : std::uint8_t
    {
        None = 0,
        Hud2D,
        PerspectiveHud,
        ScreenOverlay2D,
        ProjectedScreenEffect2D,
        WorldBillboard,
        ProjectedWorldMarker2D
    };

    constexpr Kind DirectKind(RenderPolicy::SemanticRoute route) noexcept
    {
        using R = RenderPolicy::SemanticRoute;
        switch (route)
        {
        case R::ScreenOverlay2D:
            return Kind::ScreenOverlay2D;
        case R::ProjectedScreenEffect:
            return Kind::ProjectedScreenEffect2D;
        case R::ProjectedWorld:
            return Kind::ProjectedWorldMarker2D;
        default:
            return Kind::None;
        }
    }

    constexpr bool NeedsScreenTransform(Kind kind) noexcept
    {
        return kind != Kind::None;
    }

    constexpr bool IsProjected(Kind kind) noexcept
    {
        return kind == Kind::ProjectedWorldMarker2D ||
            kind == Kind::ProjectedScreenEffect2D;
    }
}
