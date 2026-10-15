#pragma once
namespace outrun::vr::dx11::live_game_frame {
// Offscreen menu/vehicle texture passes may be interleaved with main-backbuffer
// Draws. They do not touch its native RTV/DSV only if color is routed away,
// D3D9 Z/stencil are disabled and no extra MRT is bound. This is not an
// assertion about texture parity: any subsequent unsupported main Draw aborts.
struct GameNativeOffscreenPass {
    [[nodiscard]] static constexpr bool preserve_transition(
        bool fullMode, bool wholeBackbufferSeeded, bool sameOwner,
        bool stopped, bool targetKnown) noexcept {
        return fullMode && wholeBackbufferSeeded && sameOwner &&
            !stopped && targetKnown;
    }
    [[nodiscard]] static constexpr bool source_has_no_main_writes(
        bool fullMode, bool wholeBackbufferSeeded, bool targetIsOffscreen,
        bool depthDisabled, bool stencilDisabled, bool noExtraRenderTargets,
        bool stopped) noexcept {
        return fullMode && wholeBackbufferSeeded && targetIsOffscreen &&
            depthDisabled && stencilDisabled && noExtraRenderTargets && !stopped;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
