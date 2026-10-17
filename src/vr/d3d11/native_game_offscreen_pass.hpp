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
    // A depth-writing offscreen Draw may still be isolated: it writes an
    // independently owned auxiliary D3D9 Z surface, not the main DSV.
    // The caller must prove a different canonical COM identity first.
    [[nodiscard]] static constexpr bool no_main_depth_write(
        bool depthEnabled, bool depthWritesEnabled,
        bool provenAuxiliaryDepth = false) noexcept {
        return !depthEnabled || !depthWritesEnabled || provenAuxiliaryDepth;
    }
    // A TARGET Clear may modify RT0 and every bound MRT regardless of
    // color-write masks: every color target must be isolated from the game.
    // Z/STENCIL-only Clears cannot modify color, even with main RT0 bound.
    // They are safe only with an independently identified auxiliary Z/S
    // surface. Unknown or aliased main depth always fails closed.
    [[nodiscard]] static constexpr bool isolated_auxiliary_clear(
        bool sourceSeeded, bool offscreenRt0, bool extraMrtUnbound,
        bool depthOrStencilClear, bool separateDepth,
        bool stopped, bool clearsColor = true) noexcept {
        return sourceSeeded && !stopped &&
            (!clearsColor || (offscreenRt0 && extraMrtUnbound)) &&
            (!depthOrStencilClear || separateDepth);
    }
    // Enabled D3D9 stencil testing alone does not write stencil. With the
    // *entire* stencil write mask zero, front/back ops cannot mutate main Z/S.
    // A failed mask query must never reach this predicate as a zero mask.
    [[nodiscard]] static constexpr bool no_main_stencil_write(
        bool stencilEnabled, bool maskKnown, std::uint32_t writeMask) noexcept {
        return !stencilEnabled || (maskKnown && writeMask == 0u);
    }
    // A bound auxiliary MRT writes no main color only if its own D3D9
    // COLORWRITEENABLEn mask was successfully read and is exactly zero.
    // Unlike Draw, Clear ignores COLORWRITEENABLEn and stays strict.
    [[nodiscard]] static constexpr bool inactive_extra_mrt(
        bool maskKnown, std::uint32_t writeMask) noexcept {
        return maskKnown && writeMask == 0u;
    }
    // A bound game MRT may write during a vehicle/menu render-to-texture pass
    // without modifying the seeded main frame, but only when its actual
    // IUnknown surface identity is distinct from the main backbuffer.
    // A disabled color mask is independently sufficient for Draws, never Clear.
    [[nodiscard]] static constexpr bool distinct_auxiliary_mrt(
        std::uintptr_t bound, std::uintptr_t mainBackbuffer) noexcept {
        return bound != 0u && mainBackbuffer != 0u &&
            bound != mainBackbuffer;
    }
    // A writable stencil mask on a game offscreen Draw is safe only when
    // the bound Z/stencil surface has a proven identity distinct from the
    // canonical main depth surface. Unknown write masks always fail closed.
    [[nodiscard]] static constexpr bool isolated_auxiliary_stencil_write(
        bool stencilEnabled, bool maskKnown, std::uint32_t writeMask,
        bool provenAuxiliaryDepth) noexcept {
        return stencilEnabled && maskKnown && writeMask != 0u &&
            provenAuxiliaryDepth;
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
