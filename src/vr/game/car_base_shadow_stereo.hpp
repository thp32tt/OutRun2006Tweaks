#pragma once
#include "render_semantics.hpp"

// Exact player contact-shadow producer and independent original world WVP
// proof are both required before overriding the conservative alpha route.
// The pass/projection class by itself is NOT evidence that the game's c64
// was uploaded by this shadow: an earlier car/world draw may have used the
// same perspective projection. Fence the real game upload to its original
// nonqueued producer, latched pose, shader epoch and immediate GPU draw.
namespace OutRunVR::CarShadowStereo {
struct DirectGameWvpOwner
{
    std::uint64_t currentPoseEpoch, uploadedPoseEpoch;
    std::uint64_t nextDrawSerial, uploadDrawSerial;
    std::uintptr_t currentShader, uploadShader;
    std::uint64_t currentShaderEpoch, uploadShaderEpoch;
    GameSemantic::RenderScope uploadScope;
    GameSemantic::ProducerToken uploadProducer;
    bool uploadedWhileQueued;
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
        !owner.uploadedWhileQueued;
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
