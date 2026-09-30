#pragma once

#include "dispatch_semantics.hpp"
#include "../d3d9/screen_space_policy.hpp"
#include "../d3d9/vr_pass_policy.hpp"
#include "../lifecycle/reset_replay_policy.hpp"

namespace OutRunVR::Core::RefactorContract
{
    static_assert(SemanticRouteFor(GameSemantic::RenderScope::ScreenHud) ==
        SemanticRoute::ScreenHud);
    static_assert(SemanticRouteFor(GameSemantic::RenderScope::WorldBillboard) ==
        SemanticRoute::World);
    static_assert(ScreenSpacePolicy::DirectKind(
        SemanticRoute::ProjectedWorld) ==
        ScreenSpacePolicy::Kind::ProjectedWorldMarker2D);
    static_assert(PassPolicy::AllowsWorldStereo(
        PassPolicy::RenderSemantic::World3D));
    static_assert(!PassPolicy::AllowsWorldStereo(
        PassPolicy::RenderSemantic::Unknown));
    static_assert(Lifecycle::ResetReplayHealthy(true, true));
    static_assert(!Lifecycle::ResetReplayHealthy(true, false));
    static_assert(!Lifecycle::ResetReplayHealthy(false, true));
    static_assert(!Lifecycle::ResetReplayHealthy(false, false));
}
