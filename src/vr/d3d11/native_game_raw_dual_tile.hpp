#pragma once
// Two independent source-authentic native Draw GPU tiles under one source
// epoch/fence. No synthetic pixels and no complete-frame promotion.
#include <cstdint>
#include "native_game_raw_draw_tile.hpp"
namespace outrun::vr::dx11 {
struct NativeRawDualTile {
    NativeRawTileOrigin first{}, second{};
    bool hasSecond = false;
};
[[nodiscard]] constexpr bool native_raw_dual_draw_tile(
    std::uint32_t sw, std::uint32_t sh, std::uint32_t tw,
    std::uint32_t th, NativeRawDrawExtent raster,
    std::uint32_t ordinal, NativeRawDualTile& out) noexcept {
    out = {};
    if (!native_raw_draw_tile(sw, sh, tw, th, raster, ordinal, out.first))
        return false;
    for (std::uint32_t step = 2u; step < 7u; ++step) {
        NativeRawTileOrigin next{};
        if (native_raw_draw_tile(sw, sh, tw, th, raster,
                                 ordinal + step, next) &&
            (next.x != out.first.x || next.y != out.first.y)) {
            out.second = next;
            out.hasSecond = true;
            break;
        }
    }
    return true;
}
[[nodiscard]] constexpr bool native_raw_choose_second_tile(
    std::uint32_t firstChanged, std::uint32_t secondChanged,
    bool available) noexcept {
    return available && secondChanged > firstChanged;
}
} // namespace outrun::vr::dx11
