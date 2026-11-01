#pragma once
// Opt-in source-authentic triangle-island GPU capture guidance; never
// replaces original D3D9 Draw, COM/RT identity, native GPU RGB or fences.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include "native_game_raw_fvf_clip_capture.hpp"
#include "native_game_raw_dual_tile.hpp"
namespace outrun::vr::dx11 {
// Each original list/strip/fan triangle is projected with the SAME clipped
// source geometry, then intersected with authenticated RT viewport/scissor.
// Whole-IA validation comes first: partial valid indices cannot hide a
// malformed source draw. Source buffers are borrowed only within this call.
[[nodiscard]] inline bool native_raw_fvf_island_dual_draw_tile(
    NativeRawFvfClipSpan source,
    float vx, float vy, float vw, float vh,
    std::uint32_t sw, std::uint32_t sh,
    std::uint32_t tw, std::uint32_t th,
    NativeRawDrawExtent admitted, std::uint32_t ordinal,
    NativeRawDualTile& out) noexcept {
    out = {};
    NativeRawDrawExtent assembled{};
    if (!native_raw_fvf_projected_raster(
            source, vx, vy, vw, vh, assembled) ||
        !sw || !sh || !tw || !th || tw > sw || th > sh ||
        admitted.left >= admitted.right ||
        admitted.top >= admitted.bottom) return false;
    const std::size_t active = source.indices ? source.indexCount : source.count;
    const std::size_t count = source.assembly == NativeRawFvfAssembly::TriangleList
        ? active / 3u : active - 2u;
    if (!count || count > 8192u) return false;
    bool found = false;
    NativeRawDrawExtent firstWindow{};
    const std::size_t start = static_cast<std::size_t>(ordinal) % count;
    for (std::size_t step = 0u; step < count; ++step) {
        const auto t = (start + step) % count;
        std::uint32_t indices[3]{};
        for (std::size_t j = 0u; j < 3u; ++j) {
            const auto element = source.assembly == NativeRawFvfAssembly::TriangleList
                ? t * 3u + j
                : source.assembly == NativeRawFvfAssembly::TriangleStrip
                    ? t + j : j == 0u ? 0u : t + j;
            indices[j] = source.indices
                ? source.indices[element] : static_cast<std::uint32_t>(element);
        }
        NativeRawDrawExtent triangle{};
        if (!native_raw_fvf_projected_raster(
                {source.firstClip, source.vertexStride, source.count,
                 indices, 3u, NativeRawFvfAssembly::TriangleList},
                vx, vy, vw, vh, triangle))
            continue; // fully offscreen, depth-clipped or degenerate
        triangle.left = (std::max)(triangle.left,
            (std::max)(admitted.left, assembled.left));
        triangle.top = (std::max)(triangle.top,
            (std::max)(admitted.top, assembled.top));
        triangle.right = (std::min)(triangle.right,
            (std::min)(admitted.right, assembled.right));
        triangle.bottom = (std::min)(triangle.bottom,
            (std::min)(admitted.bottom, assembled.bottom));
        if (triangle.right <= triangle.left ||
            triangle.bottom <= triangle.top) continue;
        NativeRawTileOrigin tile{};
        if (!native_raw_draw_tile(sw, sh, tw, th, triangle, 0u, tile))
            continue;
        if (!found) {
            out.first = tile;
            firstWindow = triangle;
            found = true;
        } else if (native_raw_source_tiles_disjoint(
                       out.first, tile, tw, th)) {
            out.second = tile;
            out.hasSecond = true;
            return true;
        }
    }
    if (!found) return false;
    // Preserve the existing two-GPU-tile sweep for a single large triangle.
    NativeRawDualTile within{};
    if (native_raw_swept_dual_draw_tile(
            sw, sh, tw, th, firstWindow, ordinal, within) && within.hasSecond)
        out = within;
    return true;
}
} // namespace outrun::vr::dx11
