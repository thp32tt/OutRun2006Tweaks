#pragma once
#include <cstdint>
#include "render_semantics.hpp"

// R84 exact HUD original-game matrix source at the native c64 boundary.
// A nested original queue/producers/shader callback can reselect a SpriteNode
// without another c64 write. Never attribute its previously submitted raw WVP
// to the new glyph's per-eye HUD plane. No changes to the real D3D9 HRESULT.
namespace OutRunVR::HudNativeSource
{
    using OutRunVR::GameSemantic::RenderScope;
    using OutRunVR::GameSemantic::ProducerToken;
    struct SourceStamp final
    {
        bool queueActive = false;
        RenderScope scope = RenderScope::None;
        ProducerToken producer = ProducerToken::None;
        const void* node = nullptr;
        std::uint64_t nodeEpoch = 0;
        std::uint64_t poseEpoch = 0;
        std::uintptr_t shader = 0;
        std::uint64_t shaderEpoch = 0;
        std::uint64_t drawSerial = 0;
    };

    // Converts R33's immutable physical GPU owner into a typed source stamp.
    // The runtime captures shader/pose/draw identity at the same boundary.
    constexpr SourceStamp StampPhysicalCommand(
        const OutRunVR::GameSemantic::PhysicalDrawCommand& command,
        std::uint64_t poseEpoch, std::uintptr_t shader,
        std::uint64_t shaderEpoch, std::uint64_t drawSerial) noexcept
    {
        return { command.queued, command.scope, command.producer,
                 command.queueNode, command.queueEpoch, poseEpoch,
                 shader, shaderEpoch, drawSerial };
    }

    constexpr bool IsExactHudSource(const SourceStamp& s) noexcept
    {
        if (s.scope != RenderScope::ScreenHud ||
            s.producer == ProducerToken::None || !s.poseEpoch ||
            !s.shader || !s.shaderEpoch)
            return false;
        return s.queueActive ? s.node != nullptr && s.nodeEpoch != 0
                             : s.node == nullptr;
    }

    constexpr bool SameSourceAfterNativeUpload(
        const SourceStamp& before, const SourceStamp& after) noexcept
    {
        const bool beforeHud = IsExactHudSource(before);
        const bool afterHud = IsExactHudSource(after);
        // Leave unknown world, original lens/flare, and UI paths unchanged.
        if (!beforeHud && !afterHud)
            return true;
        // Do not allow a HUD source to appear/disappear during native calls.
        if (!beforeHud || !afterHud)
            return false;
        return before.queueActive == after.queueActive &&
            before.scope == after.scope &&
            before.producer == after.producer &&
            before.node == after.node &&
            before.nodeEpoch == after.nodeEpoch &&
            before.poseEpoch == after.poseEpoch &&
            before.shader == after.shader &&
            before.shaderEpoch == after.shaderEpoch &&
            before.drawSerial == after.drawSerial;
    }
    // The original 6th/6 FVF142 SpriteNode (kind-1 plus eight clipped
    // digits) has no shader. R33's shader HUD fence does not cover it.
    struct FixedFnRankHudStamp final
    {
        GameSemantic::PhysicalDrawCommand command{};
        std::uint64_t poseEpoch = 0;
        std::uint64_t drawSerial = 0;
        std::uint32_t fvf = 0;
        bool vertexShaderAbsent = false;
    };

    constexpr bool IsExactFixedFnRankHud(
        const FixedFnRankHudStamp& s) noexcept
    {
        const auto p = s.command.producer;
        if (!s.vertexShaderAbsent || s.fvf != 0x142u ||
            !s.poseEpoch || !s.drawSerial ||
            s.command.scope != RenderScope::ScreenHud ||
            (p != ProducerToken::DispRankFirst &&
             p != ProducerToken::DispRankClipSprite))
            return false;
        return s.command.queued
            ? s.command.queueNode != nullptr && s.command.queueEpoch != 0
            : s.command.queueNode == nullptr && s.command.queueEpoch == 0;
    }

    constexpr bool SameFixedFnRankHudAfterLeft(
        const FixedFnRankHudStamp& before,
        const FixedFnRankHudStamp& after) noexcept
    {
        return IsExactFixedFnRankHud(before) &&
            IsExactFixedFnRankHud(after) &&
            before.command.scope == after.command.scope &&
            before.command.producer == after.command.producer &&
            before.command.queued == after.command.queued &&
            before.command.queueNode == after.command.queueNode &&
            before.command.queueEpoch == after.command.queueEpoch &&
            before.poseEpoch == after.poseEpoch &&
            before.drawSerial == after.drawSerial &&
            before.fvf == after.fvf &&
            before.vertexShaderAbsent == after.vertexShaderAbsent;
    }

    static_assert(!IsExactFixedFnRankHud({}));
    static_assert(!IsExactFixedFnRankHud({
        {RenderScope::ProjectedWorldMarker2D,
         ProducerToken::RankMarkerClipSprite, nullptr, 0, false, 0},
        1, 1, 0x142u, true}));
}
