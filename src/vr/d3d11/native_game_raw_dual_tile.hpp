#pragma once
// Two independent source-authentic native Draw GPU tiles under one source
// epoch/fence. No synthetic pixels and no complete-frame promotion.
#include <cstdint>
#include "native_game_raw_draw_tile.hpp"
#include "native_game_raw_gpu_capture_epoch.hpp"
#include <limits>
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
// Preserve authentic source color-write invalidation for BOTH native
// BEFORE/AFTER regions. Unknown rectangles and arithmetic overflow always
// retire the capture, never publish a stale diagnostic GPU tile.
[[nodiscard]] constexpr bool native_raw_dual_source_write_overlaps(
    std::uint32_t firstX, std::uint32_t firstY, bool hasSecond,
    std::uint32_t secondX, std::uint32_t secondY,
    std::uint32_t width, std::uint32_t height,
    const NativeRawSourcePixelRect* writes,
    std::uint32_t count) noexcept {
    constexpr auto max = (std::numeric_limits<std::uint32_t>::max)();
    if (!width || !height || firstX > max - width ||
        firstY > max - height ||
        (hasSecond && (secondX > max - width || secondY > max - height)))
        return true;
    return native_raw_source_write_overlaps_tile(
               firstX, firstY, firstX + width, firstY + height,
               writes, count) ||
           (hasSecond && native_raw_source_write_overlaps_tile(
               secondX, secondY, secondX + width, secondY + height,
               writes, count));
}
[[nodiscard]] constexpr bool native_raw_choose_second_tile(
    std::uint32_t firstChanged, std::uint32_t secondChanged,
    bool available) noexcept {
    return available && secondChanged > firstChanged;
}
} // namespace outrun::vr::dx11
