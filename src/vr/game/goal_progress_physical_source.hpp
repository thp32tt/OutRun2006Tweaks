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
