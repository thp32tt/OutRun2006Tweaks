#pragma once
#include "render_semantics.hpp"

// Exact player contact-shadow producer and independent original world WVP
// proof are both required before overriding the conservative alpha route.
namespace OutRunVR::CarShadowStereo {
constexpr bool CanUseSpatialShadow(
    GameSemantic::ProducerToken producer, GameSemantic::RenderScope scope,
    bool queued, bool verifiedOriginalWvp, bool depthDisabled,
    bool depthWrites, bool stencilEnabled, bool forcedFlat) noexcept
{
    return producer == GameSemantic::ProducerToken::CarBaseShadow &&
        scope == GameSemantic::RenderScope::WorldParticle && !queued &&
        verifiedOriginalWvp && depthDisabled && !depthWrites &&
        !stencilEnabled && !forcedFlat;
}
constexpr auto Player = GameSemantic::ProducerToken::CarBaseShadow;
constexpr auto World = GameSemantic::RenderScope::WorldParticle;
static_assert(CanUseSpatialShadow(Player,World,false,true,true,false,false,false));
static_assert(!CanUseSpatialShadow(Player,World,true,true,true,false,false,false));
static_assert(!CanUseSpatialShadow(Player,World,false,false,true,false,false,false));
static_assert(!CanUseSpatialShadow(Player,World,false,true,true,true,false,false));
static_assert(!CanUseSpatialShadow(GameSemantic::ProducerToken::None,World,false,true,true,false,false,false));
}
