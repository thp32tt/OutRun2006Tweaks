#pragma once
#include <array>
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// A successful entire-backbuffer D3D9 color Clear is the baseline for the
// first native Draw in that same scene; original D3D9 state is never changed.
struct GameNativeClearColor {
    std::uintptr_t sourceDevice = 0u, backbufferIdentity = 0u;
    std::uint32_t argb = 0u;
    // D3DFMT_X8R8G8B8 has no destination alpha: native RGBA must
    // initialize alpha as opaque for subsequent DESTALPHA blending.
    bool opaqueDestinationAlpha = false;
    bool valid = false;
    constexpr void discard() noexcept {
        sourceDevice = backbufferIdentity = 0u;
        argb = 0u;
        opaqueDestinationAlpha = false;
        valid = false;
    }
    constexpr void record(std::uintptr_t device, std::uintptr_t backbuffer,
                          std::uint32_t color, bool wholeBackbuffer,
                          bool opaqueBackbuffer = false) noexcept {
        discard();
        if (wholeBackbuffer && device != 0u && backbuffer != 0u) {
            sourceDevice = device;
            backbufferIdentity = backbuffer;
            argb = color;
            opaqueDestinationAlpha = opaqueBackbuffer;
            valid = true;
        }
    }
    [[nodiscard]] constexpr bool matches(std::uintptr_t device,
                                         std::uintptr_t backbuffer) const noexcept {
        return valid && device != 0u && backbuffer != 0u &&
               sourceDevice == device && backbufferIdentity == backbuffer;
    }
    // Menu and vehicle-preview passes may Clear an auxiliary RT0 using the
    // game device. A color-only offscreen Clear does not modify the previously
    // verified full-size game backbuffer. Keep its native Draw batch intact,
    // but never carry it over a main-target, Z or stencil Clear.
    [[nodiscard]] constexpr bool preserves_offscreen_color_only(
        std::uintptr_t device, std::uintptr_t backbuffer,
        std::uintptr_t target, bool colorOnly,
        bool batchStopped) const noexcept {
        return colorOnly && !batchStopped &&
            matches(device, backbuffer) &&
            target != 0u && target != backbuffer;
    }
    // Disable writes to the absent X8 alpha plane for every native draw.
    // Mismatched or partial/invalid clears and A8 retain source write masks.
    [[nodiscard]] constexpr std::uint32_t native_write_mask(
        std::uintptr_t device, std::uintptr_t backbuffer,
        std::uint32_t requested) const noexcept {
        return matches(device, backbuffer) && opaqueDestinationAlpha
            ? requested & ~std::uint32_t{0x08u} : requested;
    }
    [[nodiscard]] constexpr std::array<float, 4> native_color(
        std::uintptr_t device, std::uintptr_t backbuffer,
        const std::array<float, 4>& fallback) const noexcept {
        if (!matches(device, backbuffer)) return fallback;
        constexpr float scale = 1.0f / 255.0f;
        return {float((argb >> 16) & 255u) * scale,
                float((argb >> 8) & 255u) * scale,
                float(argb & 255u) * scale,
                opaqueDestinationAlpha ? 1.0f :
                    float((argb >> 24) & 255u) * scale};
    }
};
} // namespace outrun::vr::dx11::live_game_frame
