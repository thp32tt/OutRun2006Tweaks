#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Game Draw/DrawIndexed can change A8 destination alpha or native depth even
// without an RGB write. Unlike the RGB-only diagnostic inset, the full-size
// mirror must retain those operations so later menu/car/race passes can use
// their destination-alpha blend and depth-test results.
struct GameNativeMaskedDraw {
    // A real D3D9 Draw/DrawIndexed with no color, depth or stencil writes
    // consumes a source ordinal but contributes no backbuffer pixels. Treat
    // it like a zero-primitive call only after all writable MRTs are excluded.
    // Never invent a native GPU Draw or skip an unproved depth/stencil pass.
    [[nodiscard]] static constexpr bool no_target_write_source_draw(
        bool fullMode, bool clearedGameBackbuffer, std::uint32_t colorMask,
        bool depthEnabled, bool depthWriteEnabled, bool stencilEnabled,
        bool extraRenderTargetBound) noexcept {
        return fullMode && clearedGameBackbuffer && colorMask == 0u &&
            (!depthEnabled || !depthWriteEnabled) && !stencilEnabled &&
            !extraRenderTargetBound;
    }
    [[nodiscard]] static constexpr bool accepts_source_mask(
        std::uint32_t d3d9Mask, bool fullFrame, bool targetHasAlpha,
        bool nativeDepthWrite) noexcept {
        constexpr std::uint32_t kRgb = 0x07u; // D3DCOLORWRITEENABLE_RED/GREEN/BLUE
        constexpr std::uint32_t kAlpha = 0x08u; // D3DCOLORWRITEENABLE_ALPHA
        constexpr std::uint32_t kAll = kRgb | kAlpha;
        if ((d3d9Mask & ~kAll) != 0u) return false;
        if ((d3d9Mask & kRgb) != 0u) return true;
        // An A8 alpha-only pass feeds subsequent DESTALPHA blends; a true
        // depth-writing prepass updates DSV even with no color writes.
        // X8 without depth writes and zero-effect passes fail closed.
        return fullFrame &&
            ((targetHasAlpha && (d3d9Mask & kAlpha) != 0u) || nativeDepthWrite);
    }
    [[nodiscard]] static constexpr std::uint8_t effective_native_mask(
        std::uint32_t d3d9Mask, bool targetHasAlpha) noexcept {
        return static_cast<std::uint8_t>(
            d3d9Mask & (targetHasAlpha ? 0x0fu : 0x07u));
    }
};
} // namespace outrun::vr::dx11::live_game_frame
