#pragma once
// Replay D3D9 ColorFill tiles before the first full-size native game Draw.
// D3D11.1 ClearView and D3D11.0 bounded GPU raster both preserve ordered pixels.
#include "native_game_source_mutation.hpp"
#include <array>
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
struct GameNativePreDrawTile {
    std::int64_t left{}, top{}, right{}, bottom{};
    std::array<float, 4> rgba{};
};
template<class ClearView, class Raster>
[[nodiscard]] inline bool game_native_replay_pre_draw_fills(
    const GameNativePreDrawFills& fills, std::uintptr_t owner,
    std::uintptr_t target, std::uint32_t width, std::uint32_t height,
    bool opaqueAlpha, bool clearViewAvailable,
    ClearView&& clearView, Raster&& raster) noexcept {
    if (!fills.replay_ready(owner, target, width, height)) return false;
    constexpr float scale = 1.0f / 255.0f;
    for (std::uint32_t i = 0u; i < fills.count; ++i) {
        const auto& fill = fills.entries[i];
        const GameNativePreDrawTile tile{
            fill.left, fill.top, fill.right, fill.bottom,
            {{float((fill.argb >> 16) & 255u) * scale,
              float((fill.argb >> 8) & 255u) * scale,
              float(fill.argb & 255u) * scale,
              opaqueAlpha ? 1.0f : float((fill.argb >> 24) & 255u) * scale}}};
        if (!(clearViewAvailable ? clearView(tile) : raster(tile)))
            return false;
    }
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
