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
}
