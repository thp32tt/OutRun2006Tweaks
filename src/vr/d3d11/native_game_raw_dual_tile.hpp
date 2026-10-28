#pragma once
// Two independent source-authentic native Draw GPU tiles under one source
// epoch/fence. No synthetic pixels and no complete-frame promotion.
#include <cstdint>
#include "native_game_raw_draw_tile.hpp"
#include "native_game_raw_gpu_capture_epoch.hpp"
#include "native_game_raw_partial_present_tile.hpp"
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
// Place the second TRUE native GPU Draw crop beside the first, or below it
// for a narrow source Present. Never overlap the two real diagnostic images,
// escape the caller-verified source crop, or enlarge to a fictitious frame.
[[nodiscard]] constexpr bool native_raw_secondary_present_tile(
    const NativeRawPresentTile& primary,
    std::int64_t cropLeft, std::int64_t cropTop,
    std::int64_t cropRight, std::int64_t cropBottom,
    NativeRawPresentTile& secondary) noexcept {
    secondary = {};
    constexpr std::int64_t margin = 8, gap = 8;
    if (cropLeft < 0 || cropTop < 0 || cropLeft >= cropRight ||
        cropTop >= cropBottom || !primary.copyWidth || !primary.copyHeight ||
        primary.destinationX < cropLeft + margin ||
        primary.destinationY < cropTop + margin ||
        primary.destinationX > cropRight - margin ||
        primary.destinationY > cropBottom - margin ||
        primary.copyWidth > cropRight - margin - primary.destinationX ||
        primary.copyHeight > cropBottom - margin - primary.destinationY)
        return false;
    secondary = primary;
    const auto w = static_cast<std::int64_t>(primary.copyWidth);
    const auto h = static_cast<std::int64_t>(primary.copyHeight);
    if (primary.destinationX - cropLeft >= margin + gap + w) {
        secondary.destinationX = primary.destinationX - gap - w;
        return true;
    }
    if (cropBottom - margin - primary.destinationY >= h + gap + h) {
        secondary.destinationY = primary.destinationY + h + gap;
        return true;
    }
    secondary = {};
    return false;
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
