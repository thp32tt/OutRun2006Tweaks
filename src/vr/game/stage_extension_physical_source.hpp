#pragma once
#include "render_semantics.hpp"
#include <cstdint>

// Exact physical GPU submission source for the complete stage +TIME family:
// both queued sprite children and direct numeric D3DX glyph batches. A
// successful native LEFT Draw may reenter a different producer/shader/queue.
// The prepared RIGHT projection may only be used for the same source.
namespace OutRunVR::StageExtensionPhysical
{
    struct Source
    {
        GameSemantic::RenderScope scope = GameSemantic::RenderScope::None;
        GameSemantic::ProducerToken producer = GameSemantic::ProducerToken::None;
        bool queued = false;
        const void* node = nullptr;
        std::uint64_t queueEpoch = 0;
        std::uint64_t poseEpoch = 0;
        std::uint64_t topLevelDrawSerial = 0;
        std::uintptr_t shader = 0;
        std::uint64_t shaderEpoch = 0;
        // Preserve the original game's physical c64 upload generation, not
        // the already stereo-corrected live GPU c64. Zero/zero means unknown.
        std::uint64_t rawWvpWriteSerial = 0;
        std::uint64_t rawWvpDrawSerial = 0;
    };

    // R84 receives the last ORIGINAL game c64 write separately from its
    // private left/right eye uploads. An available write from a different
    // vertex shader is NOT missing evidence: it is a foreign physical owner.
    // Reject that candidate before the left eye rather than silently
    // converting its stale write into the unknown (zero/zero) fallback.
    // Only a genuinely unavailable original-write tracker may use fallback.
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

    // Source-header regressions execute in the real Windows R84 TU.
    // A previous world/GOAL shader's c64 must not be used for +TIME stereo.
    static_assert(MatchesCapturedOriginalWvp(
        true, 0x100, 9, 0x100, 9, 42, 40));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 9, 0x200, 9, 42, 40));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 9, 0x100, 8, 42, 40));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 9, 0x100, 9, 0, 40));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 9, 0x100, 9, 42, 0));
    static_assert(!MatchesCapturedOriginalWvp(
        true, 0x100, 0, 0x100, 0, 42, 40));
    static_assert(MatchesCapturedOriginalWvp(
        true, 0, 0, 0, 0, 42, 40));
    static_assert(MatchesCapturedOriginalWvp(
        false, 0x100, 9, 0x200, 8, 0, 0));

    constexpr bool IsStage(const Source& s) noexcept
    {
        return s.scope == GameSemantic::RenderScope::ScreenHud &&
            s.producer == GameSemantic::ProducerToken::StageExtensionTime;
    }

    constexpr bool IsValid(const Source& s) noexcept
    {
        return IsStage(s) && s.poseEpoch != 0 &&
            s.topLevelDrawSerial != 0 &&
            (s.shader == 0 || s.shaderEpoch != 0) &&
            ((s.rawWvpWriteSerial == 0) == (s.rawWvpDrawSerial == 0)) &&
            (s.queued ? (s.node != nullptr && s.queueEpoch != 0)
                      : (s.node == nullptr && s.queueEpoch == 0));
    }

    constexpr bool SameAfterNativeLeft(const Source& a, const Source& b) noexcept
    {
        return IsValid(a) && IsValid(b) &&
            a.scope == b.scope && a.producer == b.producer &&
            a.queued == b.queued && a.node == b.node &&
            a.queueEpoch == b.queueEpoch &&
            a.poseEpoch == b.poseEpoch &&
            a.topLevelDrawSerial == b.topLevelDrawSerial &&
            a.shader == b.shader && a.shaderEpoch == b.shaderEpoch &&
            a.rawWvpWriteSerial == b.rawWvpWriteSerial &&
            a.rawWvpDrawSerial == b.rawWvpDrawSerial;
    }
}
