#pragma once
#include "render_semantics.hpp"
#include <cstdint>

// Original OutRun GOAL progress, time helpers, Sumo stage results and proven
// B9200 glyphs: fence direct or queued GPU submission for *both* R84 eye
// paths, not the earlier ID3DXSprite::Draw registration. +TIME has its own
// distinct original producer/fence and must not be promoted through this.
namespace OutRunVR::GoalPhysical
{
    struct Source
    {
        GameSemantic::RenderScope scope = GameSemantic::RenderScope::None;
        GameSemantic::ProducerToken producer = GameSemantic::ProducerToken::None;
        bool queued = false;
        const void* node = nullptr;
        std::uint64_t queueEpoch = 0;
        std::uint64_t poseEpoch = 0;
        std::uint64_t drawSerial = 0;
        std::uintptr_t shader = 0;
        std::uint64_t shaderEpoch = 0;
        // The ORIGINAL game c64 generation (not stereo eye uploads).
        // A complete zero/zero pair preserves missing-evidence fallback.
        std::uint64_t rawWvpWriteSerial = 0;
        std::uint64_t rawWvpDrawSerial = 0;
    };
    // Only original-game c64 writes identify GOAL source generations.
    // An unavailable/incomplete tracker pair must remain the existing
    // zero/zero conservative fallback, never half-initialized or a live
    // stereo-adjusted c64 upload borrowed from another eye.
    constexpr Source StampOriginalGameWvpGeneration(
        Source source, bool captured, std::uint64_t writeSerial,
        std::uint64_t drawSerial) noexcept
    {
        const bool complete = captured && writeSerial != 0 && drawSerial != 0;
        source.rawWvpWriteSerial = complete ? writeSerial : 0;
        source.rawWvpDrawSerial = complete ? drawSerial : 0;
        return source;
    }
    // Fixed-function GOAL sprite and D3DX glyph draws consume FVF/XY
    // coordinates, not a vertex-shader c64 WVP. Reusing a preceding world's
    // original c64 generation can veto the right eye even while both native
    // GOAL sprites retain a valid queue, pose and physical draw source.
    // Shader-backed results still require their own exact game c64 writer.
    constexpr bool RequiresOriginalShaderC64(std::uintptr_t shader) noexcept
    {
        return shader != 0;
    }
    static_assert(!RequiresOriginalShaderC64(0));
    static_assert(RequiresOriginalShaderC64(0x100));

    // Use one generation-stamp rule for both R30 fixed-function/XYZRHW and
    // R33 shader HUD submission. Never import unrelated VS constants into
    // a fixed-function result; do not weaken the shader-backed source fence.
    constexpr Source StampPhysicalGameWvpGeneration(
        Source source, bool captured, std::uint64_t writeSerial,
        std::uint64_t drawSerial) noexcept
    {
        return RequiresOriginalShaderC64(source.shader)
            ? StampOriginalGameWvpGeneration(
                source, captured, writeSerial, drawSerial)
            : StampOriginalGameWvpGeneration(source, false, 0, 0);
    }

    // The native GOAL/result Draw may follow an original c64 write from a
    // *different* vertex shader or shader generation (for example, a racing
    // world pass reentering the result queue). Captured foreign provenance
    // must never be recast as missing evidence and accepted for either eye.
    // R32's private left/right uploads are not original game writes.
    constexpr bool MatchesCapturedOriginalWvp(
        bool captured, std::uintptr_t physicalShader,
        std::uint64_t physicalShaderEpoch,
        std::uintptr_t writtenShader, std::uint64_t writtenShaderEpoch,
        std::uint64_t writeSerial, std::uint64_t drawSerial) noexcept
    {
        return !captured ||
            (writeSerial != 0 && drawSerial != 0 &&
             physicalShader == writtenShader &&
             physicalShaderEpoch == writtenShaderEpoch &&
             (physicalShader == 0 || physicalShaderEpoch != 0));
    }
    static_assert(MatchesCapturedOriginalWvp(
        true, 0x100, 7, 0x100, 7, 4, 3));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 7, 0x200, 7, 4, 3));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 7, 0x100, 6, 4, 3));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 7, 0x100, 7, 0, 3));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 7, 0x100, 7, 4, 0));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 0, 0x100, 0, 4, 3));
    static_assert(MatchesCapturedOriginalWvp(
        true, 0, 0, 0, 0, 4, 3)); // original unbound shader
    static_assert(MatchesCapturedOriginalWvp(
        false, 0x100, 7, 0x200, 6, 0, 0)); // genuinely absent
    constexpr bool IsGoal(const Source& s) noexcept
    {
        return GameSemantic::CanReprojectFiniteResultHudPlane(s.scope, s.producer) &&
            s.producer != GameSemantic::ProducerToken::StageExtensionTime;
    }
    constexpr bool IsValid(const Source& s) noexcept
    {
        return IsGoal(s) && s.poseEpoch != 0 && s.drawSerial != 0 &&
            (s.shader == 0 || s.shaderEpoch != 0) &&
            ((s.rawWvpWriteSerial == 0) == (s.rawWvpDrawSerial == 0)) &&
            (s.queued ? s.node != nullptr && s.queueEpoch != 0
                      : s.node == nullptr && s.queueEpoch == 0);
    }
    constexpr bool SameAfterNativeLeft(const Source& a, const Source& b) noexcept
    {
        return IsValid(a) && IsValid(b) && a.scope == b.scope &&
            a.producer == b.producer && a.queued == b.queued &&
            a.node == b.node && a.queueEpoch == b.queueEpoch &&
            a.poseEpoch == b.poseEpoch && a.drawSerial == b.drawSerial &&
            a.shader == b.shader && a.shaderEpoch == b.shaderEpoch &&
            a.rawWvpWriteSerial == b.rawWvpWriteSerial &&
            a.rawWvpDrawSerial == b.rawWvpDrawSerial;
    }
    static_assert(!IsGoal(Source{}));
    static_assert(!IsGoal(Source{GameSemantic::RenderScope::ScreenHud,
        GameSemantic::ProducerToken::StageExtensionTime}));
    static_assert(IsGoal(Source{GameSemantic::RenderScope::ScreenHud,
        GameSemantic::ProducerToken::ResultProgress}));
}
