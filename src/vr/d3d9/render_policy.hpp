#pragma once

#include "vr/game/render_semantics.hpp"

#include <cstdint>

namespace OutRunVR::RenderPolicy
{
    enum class SemanticRoute : std::uint8_t
    {
        None = 0,
        ScreenHud,
        ScreenOverlay2D,
        ProjectedWorld,
        ProjectedScreenEffect,
        World,
        Sky,
        SceneEffect,
        Reflection
    };

    constexpr SemanticRoute RouteFor(
        GameSemantic::RenderScope scope) noexcept
    {
        using S = GameSemantic::RenderScope;
        switch (scope)
        {
        case S::ScreenHud:
            return SemanticRoute::ScreenHud;
        case S::ScreenOverlay2D:
            return SemanticRoute::ScreenOverlay2D;
        case S::ProjectedWorldMarker2D:
            return SemanticRoute::ProjectedWorld;
        case S::ProjectedScreenEffect2D:
            return SemanticRoute::ProjectedScreenEffect;
        case S::WorldParticle:
        case S::WorldBillboard:
            return SemanticRoute::World;
        case S::SkyGlow:
            return SemanticRoute::Sky;
        case S::SceneEffect:
            return SemanticRoute::SceneEffect;
        case S::ReflectionCube:
            return SemanticRoute::Reflection;
        default:
            return SemanticRoute::None;
        }
    }

    constexpr bool IsScreenOwned(SemanticRoute route) noexcept
    {
        return route == SemanticRoute::ScreenHud ||
            route == SemanticRoute::ScreenOverlay2D ||
            route == SemanticRoute::ProjectedWorld ||
            route == SemanticRoute::ProjectedScreenEffect;
    }

    constexpr bool IsWorldOwned(SemanticRoute route) noexcept
    {
        return route == SemanticRoute::World ||
            route == SemanticRoute::ProjectedWorld;
    }
}
