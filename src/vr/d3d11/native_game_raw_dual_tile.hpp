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
// Source readback regions must be non-overlapping in either physical axis.
// Compare unsigned differences without converting D3D11 coordinates to
// signed types or overflowing x + width at the caller's pixel limits.
[[nodiscard]] constexpr bool native_raw_source_tiles_disjoint(
    NativeRawTileOrigin a, NativeRawTileOrigin b,
    std::uint32_t width, std::uint32_t height) noexcept {
    if (!width || !height) return false;
    const auto deltaX = a.x >= b.x ? a.x - b.x : b.x - a.x;
    const auto deltaY = a.y >= b.y ? a.y - b.y : b.y - a.y;
    return deltaX >= width || deltaY >= height;
}
[[nodiscard]] constexpr bool native_raw_dual_draw_tile(
    std::uint32_t sw, std::uint32_t sh, std::uint32_t tw,
    std::uint32_t th, NativeRawDrawExtent raster,
    std::uint32_t ordinal, NativeRawDualTile& out) noexcept {
    out = {};
    if (!native_raw_draw_tile(sw, sh, tw, th, raster, ordinal, out.first))
        return false;
    // Different origins do NOT imply independent pixels: small HUD/menu
    // viewports can cause two largely overlapping GPU copies. Distinct
    // RAW proof requires disjoint physical source rectangles.
    NativeRawTileOrigin samples[5]{out.first};
    bool valid[5]{true, false, false, false, false};
    for (std::uint32_t step = 1u; step < 5u; ++step)
        valid[step] = native_raw_draw_tile(sw, sh, tw, th, raster,
                                           ordinal + step, samples[step]);
    // Try the rotating center/corner anchor first; if it straddles both
    // halves of a narrow menu strip, another TWO real source tiles may
    // still fit. Search all five authenticated anchors before falling
    // back to one tile. No pixels are duplicated or extrapolated.
    for (std::uint32_t first = 0u; first < 5u; ++first) {
        if (!valid[first]) continue;
        for (std::uint32_t second = first + 1u; second < 5u; ++second) {
            if (!valid[second] || !native_raw_source_tiles_disjoint(
                    samples[first], samples[second], tw, th))
                continue;
            out.first = samples[first];
            out.second = samples[second];
            out.hasSecond = true;
            return true;
        }
    }
    return true;
}
// Large menu/race raster: rotate authentic PRE/POST GPU copies through
// the source viewport, not only the previous center/corner positions.
// This is sampling only. GPU fence, RGB delta and original D3D9 Present
// identity/dirty-region proofs still own EVERY visible pixel.
[[nodiscard]] constexpr bool native_raw_swept_dual_draw_tile(
    std::uint32_t sw, std::uint32_t sh, std::uint32_t tw,
    std::uint32_t th, NativeRawDrawExtent raster,
    std::uint32_t ordinal, NativeRawDualTile& out) noexcept {
    out = {};
    if (!native_raw_draw_tile(sw, sh, tw, th, raster, ordinal, out.first))
        return false;
    const auto l = (std::max)(std::int64_t{0}, raster.left);
    const auto t = (std::max)(std::int64_t{0}, raster.top);
    const auto r = (std::min)(std::int64_t{sw}, raster.right);
    const auto b = (std::min)(std::int64_t{sh}, raster.bottom);
    const auto spanW = static_cast<std::uint64_t>(r - l);
    const auto spanH = static_cast<std::uint64_t>(b - t);
    const auto columns = 1u + (spanW - 1u) / tw;
    const auto rows = 1u + (spanH - 1u) / th;
    const std::uint64_t cells = columns * rows;
    if (cells < 2u)
        return native_raw_dual_draw_tile(
            sw, sh, tw, th, raster, ordinal, out);
    // 64-bit intermediates also keep large valid UINT coordinates safe.
    // Copies can extend outside the raster, but NEVER outside the real RT.
    // Unchanged pixels outside the source Draw cannot be published.
    const auto sample = [&](std::uint64_t index) noexcept {
        const auto x = static_cast<std::uint64_t>(l) +
            (index % columns) * tw;
        const auto y = static_cast<std::uint64_t>(t) +
            (index / columns) * th;
        return NativeRawTileOrigin{
            static_cast<std::uint32_t>((std::min)(
                x, std::uint64_t{sw - tw})),
            static_cast<std::uint32_t>((std::min)(
                y, std::uint64_t{sh - th}))};
    };
    // One real Draw capture advances one source cell. The prior 2*ordinal
    // stride skipped every odd-numbered cell on even-size menu/car grids;
    // the half-grid second tile then skipped the SAME missing cells whenever
    // the grid size was divisible by four. Use a coprime unit stride so all
    // genuine raster cells are eventually sampled, without fabricating
    // pixels or relaxing any source/PRESENT/fence admission.
    const auto firstIndex = std::uint64_t{ordinal} % cells;
    out.first = sample(firstIndex);
    // Prefer a far second tile, then try nearby real cells if an edge
    // clamp would make the GPU source regions overlap.
    const auto half = cells / 2u + cells % 2u;
    auto secondIndex = firstIndex >= cells - half
        ? firstIndex - (cells - half) : firstIndex + half;
    for (std::uint32_t attempt = 0u; attempt < 8u &&
         attempt < cells; ++attempt) {
        const auto candidate = sample(secondIndex);
        if (native_raw_source_tiles_disjoint(
                out.first, candidate, tw, th)) {
            out.second = candidate;
            out.hasSecond = true;
            break;
        }
        secondIndex = secondIndex + 1u == cells ? 0u : secondIndex + 1u;
    }
    // Never label an overlapping/stale second readback as new native RGB.
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
