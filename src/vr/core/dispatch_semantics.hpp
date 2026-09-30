#pragma once

#include "../game/render_semantics.hpp"
#include "../d3d9/render_policy.hpp"

namespace OutRunVR::Core
{
    using SemanticRoute = RenderPolicy::SemanticRoute;

    constexpr SemanticRoute SemanticRouteFor(
        GameSemantic::RenderScope scope) noexcept
    {
        return RenderPolicy::RouteFor(scope);
    }

    static_assert(SemanticRouteFor(
        GameSemantic::RenderScope::ScreenHud) ==
        SemanticRoute::ScreenHud);
    static_assert(SemanticRouteFor(
        GameSemantic::RenderScope::WorldBillboard) ==
        SemanticRoute::World);
    static_assert(SemanticRouteFor(
        GameSemantic::RenderScope::ProjectedWorldMarker2D) ==
        SemanticRoute::ProjectedWorld);
    static_assert(SemanticRouteFor(
        GameSemantic::RenderScope::SkyGlow) ==
        SemanticRoute::Sky);
}
