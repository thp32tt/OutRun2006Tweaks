#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// A D3D9 FVF Draw with sRGB output requires the opt-in native full-size
// render target with paired linear/sRGB views. The inset has only linear
// output and must leave sRGB game Draw/Present on the original D3D9 path.
struct GameNativeSrgbDraw final {
    [[nodiscard]] static constexpr bool admit(
        std::uint32_t gameWriteState, bool fullFrame) noexcept {
        return gameWriteState == 0u ||
               (fullFrame && gameWriteState == 1u);
    }
    [[nodiscard]] static constexpr bool uses_srgb(
        std::uint32_t gameWriteState) noexcept {
        return gameWriteState == 1u;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
