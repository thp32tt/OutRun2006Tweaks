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
