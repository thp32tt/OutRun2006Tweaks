#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Offscreen menu/vehicle texture passes may be interleaved with main-backbuffer
// Draws. They do not touch the native main RTV when color is routed away,
// nor the main DSV when Z is disabled OR enabled read-only (ZWRITEENABLE=FALSE),
// stencil is disabled and no extra MRT is bound. The original D3D9 offscreen
// texture still renders; subsequent main draws must independently pass native
// texture/state admission. An unproved main writer aborts the full frame.
struct GameNativeOffscreenPass {
    // D3D9 supports up to four simultaneous render targets. An adapter may
    // expose only one; its nonexistent extra slots must never be queried.
    [[nodiscard]] static constexpr bool valid_mrt_count(
        std::uint32_t count) noexcept {
        return count >= 1u && count <= 4u;
    }
    [[nodiscard]] static constexpr bool preserve_transition(
        bool fullMode, bool wholeBackbufferSeeded, bool sameOwner,
        bool stopped, bool targetKnown) noexcept {
        return fullMode && wholeBackbufferSeeded && sameOwner &&
            !stopped && targetKnown;
    }
    [[nodiscard]] static constexpr bool no_main_depth_write(
        bool depthEnabled, bool depthWritesEnabled) noexcept {
        return !depthEnabled || !depthWritesEnabled;
    }
    // Preserve actual menu/vehicle offscreen Clear calls only when neither
    // the canonical main RT0, any extra MRT, nor the seeded main depth can
    // be written. A Z/stencil Clear bypasses D3D9 ZWRITEENABLE: only a
    // distinct, proven depth surface is safe; merely being on RT0 offscreen
    // does not protect the main depth buffer.
    [[nodiscard]] static constexpr bool isolated_auxiliary_clear(
        bool sourceSeeded, bool offscreenRt0, bool extraMrtUnbound,
        bool depthOrStencilClear, bool separateDepth,
        bool stopped) noexcept {
        return sourceSeeded && offscreenRt0 && extraMrtUnbound && !stopped &&
            (!depthOrStencilClear || separateDepth);
    }
    [[nodiscard]] static constexpr bool source_has_no_main_writes(
        bool fullMode, bool wholeBackbufferSeeded, bool targetIsOffscreen,
        bool noMainDepthWrites, bool stencilDisabled, bool noExtraRenderTargets,
        bool stopped) noexcept {
        return fullMode && wholeBackbufferSeeded && targetIsOffscreen &&
            noMainDepthWrites && stencilDisabled && noExtraRenderTargets && !stopped;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
