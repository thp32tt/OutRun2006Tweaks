#pragma once
#include "render_semantics.hpp"
#include <cmath>

// Exact player contact-shadow producer and independent original world WVP
// proof are both required before overriding the conservative alpha route.
// The pass/projection class by itself is NOT evidence that the game's c64
// was uploaded by this shadow: an earlier car/world draw may have used the
// same perspective projection. Fence the real game upload to its original
// nonqueued producer, latched pose, shader epoch and immediate GPU draw.
namespace OutRunVR::CarShadowStereo {
// Original game alpha is not necessarily clamped to [0,1]. Preserve the
// game's value/sign, but never pass a NaN/Inf to D3D9 shader state. Stage
// the result before entering the shadow matrix and GPU render-state scope.
inline bool ValidScaledAlpha(float raw, float opacity, float& out) noexcept
{
    if (!std::isfinite(raw) || !std::isfinite(opacity) || opacity <= 0.f)
        return false;
    const float candidate = raw * opacity;
    if (!std::isfinite(candidate))
        return false;
    out = candidate;
    return true;
}

struct DirectGameWvpOwner
{
    std::uint64_t currentPoseEpoch, uploadedPoseEpoch;
    std::uint64_t nextDrawSerial, uploadDrawSerial;
    std::uintptr_t currentShader, uploadShader;
    std::uint64_t currentShaderEpoch, uploadShaderEpoch;
    GameSemantic::RenderScope uploadScope;
    GameSemantic::ProducerToken uploadProducer;
    // A queue node is the live ownership proof. queueEpoch is only a
    // monotonically increasing diagnostic generation and stays nonzero
    // after EndSpriteQueueNode; it must not veto subsequent direct draws.
    const void* uploadedQueueNode;
    std::uint64_t historicalQueueEpoch;
};

constexpr bool OwnsDirectGameWvp(const DirectGameWvpOwner& owner) noexcept
{
    return owner.currentPoseEpoch != 0 &&
        owner.currentPoseEpoch == owner.uploadedPoseEpoch &&
        owner.nextDrawSerial > owner.uploadDrawSerial &&
        owner.nextDrawSerial - owner.uploadDrawSerial == 1u &&
        owner.currentShader != 0 &&
        owner.currentShader == owner.uploadShader &&
        owner.currentShaderEpoch != 0 &&
        owner.currentShaderEpoch == owner.uploadShaderEpoch &&
        owner.uploadScope == GameSemantic::RenderScope::WorldParticle &&
        owner.uploadProducer == GameSemantic::ProducerToken::CarBaseShadow &&
        owner.uploadedQueueNode == nullptr;
}

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