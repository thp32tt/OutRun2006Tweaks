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

// Only one original player-car shadow source can own both native eye draws.
// A nested callback may overwrite game c64, shader or latched pose after the
// left draw. Guard the right-eye submission without repeating the left draw.
struct StereoDrawSource
{
    std::uint64_t uploadSerial = 0, uploadDraw = 0;
    std::uint64_t poseEpoch = 0, uploadPoseEpoch = 0;
    std::uint64_t drawSerial = 0, shaderEpoch = 0;
    std::uintptr_t shader = 0;
    std::uint32_t poseSequence = 0;
    bool exactSource = false;
};
// R30 originally admits this direct shadow only when the last original
// game c64 was written for the *current* top-level GPU draw. A nested game
// callback can replace it between R30 classification and native LEFT.
// Validate the same source/generation again before either physical eye.
// drawSerial is the current completed top-level serial; R30's next serial
// must be exactly uploadDraw + 1 (without wrapping).
constexpr bool IsCoherentBeforeNativeLeft(
    const StereoDrawSource& source) noexcept
{
    return source.exactSource &&
        source.uploadSerial != 0 && source.uploadDraw != 0 &&
        source.drawSerial != 0 &&
        source.uploadDraw == source.drawSerial &&
        source.poseEpoch != 0 &&
        source.poseEpoch == source.uploadPoseEpoch &&
        source.shaderEpoch != 0 && source.shader != 0 &&
        source.poseSequence != 0;
}

// Both original-source identity and the native draw generation must still
// match immediately before the left eye; prior car/world matrices are unsafe.
static_assert(IsCoherentBeforeNativeLeft(
    {11, 40, 30, 30, 40, 50, 0x100, 60, true}));
static_assert(!IsCoherentBeforeNativeLeft(
    {11, 39, 30, 30, 40, 50, 0x100, 60, true}));
static_assert(!IsCoherentBeforeNativeLeft(
    {0, 40, 30, 30, 40, 50, 0x100, 60, true}));

constexpr bool SameStereoDrawSource(
    const StereoDrawSource& a, const StereoDrawSource& b) noexcept
{
    return a.exactSource && b.exactSource &&
        a.uploadSerial != 0 && a.uploadSerial == b.uploadSerial &&
        a.uploadDraw == b.uploadDraw &&
        a.poseEpoch != 0 && a.poseEpoch == a.uploadPoseEpoch &&
        a.poseEpoch == b.poseEpoch && b.poseEpoch == b.uploadPoseEpoch &&
        a.drawSerial != 0 && a.drawSerial == b.drawSerial &&
        a.shaderEpoch != 0 && a.shaderEpoch == b.shaderEpoch &&
        a.shader != 0 && a.shader == b.shader &&
        a.poseSequence != 0 && a.poseSequence == b.poseSequence;
}
static_assert(SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,30,30,40,50,0x100,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {12,20,30,30,40,50,0x100,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,21,30,30,40,50,0x100,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,31,31,40,50,0x100,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,30,30,41,50,0x100,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,30,30,40,51,0x100,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,30,30,40,50,0x200,60,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,30,30,40,50,0x100,61,true}));
static_assert(!SameStereoDrawSource(
    {11,20,30,30,40,50,0x100,60,true}, {11,20,30,30,40,50,0x100,60,false}));

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