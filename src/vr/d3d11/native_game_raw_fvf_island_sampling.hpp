#pragma once
// Opt-in source-authentic triangle-island GPU capture guidance; never
// replaces original D3D9 Draw, COM/RT identity, native GPU RGB or fences.
#include <algorithm>
#include <array>
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
    NativeRawDualTile& out,
    const NativeRawFvfRaster* rasterState = nullptr) noexcept {
    out = {};
    NativeRawDrawExtent assembled{};
    if (!native_raw_fvf_projected_raster(
            source, vx, vy, vw, vh, assembled, &admitted, rasterState) ||
        !sw || !sh || !tw || !th || tw > sw || th > sh ||
        admitted.left >= admitted.right ||
        admitted.top >= admitted.bottom) return false;
    const std::size_t active = source.indices ? source.indexCount : source.count;
    const std::size_t count = source.assembly == NativeRawFvfAssembly::TriangleList
        ? active / 3u : active - 2u;
    if (!count || count > 8192u) return false;
    // Source-polygon/scissor clipping (not the AABB overlap) determines
    // which genuine triangles can produce RGB in this game's source target.
    // Use that visible population for GPU capture phasing. Menus and race
    // meshes can contain thousands of fully clipped valid IA primitives;
    // their inclusion previously stranded the same RGB crop for hundreds
    // of authentic Draws. Whole-IA validity above is never relaxed.
    const auto projected_triangle = [&](std::size_t t,
                                        NativeRawDrawExtent& triangle,
                                        NativeRawFvfInteriorSample* interior = nullptr) noexcept {
        std::uint32_t indices[3]{};
        for (std::size_t j = 0u; j < 3u; ++j) {
            const auto element = source.assembly == NativeRawFvfAssembly::TriangleList
                ? t * 3u + j
                : source.assembly == NativeRawFvfAssembly::TriangleStrip
                    ? t + ((t & 1u) && j < 2u ? 1u - j : j)
                    : j == 0u ? 0u : t + j;
            indices[j] = source.indices
                ? source.indices[element] : static_cast<std::uint32_t>(element);
        }
        if (!native_raw_fvf_projected_raster(
                {source.firstClip, source.vertexStride, source.count,
                 indices, 3u, NativeRawFvfAssembly::TriangleList},
                vx, vy, vw, vh, triangle, &admitted, rasterState, interior))
            return false;
        triangle.left = (std::max)(triangle.left,
            (std::max)(admitted.left, assembled.left));
        triangle.top = (std::max)(triangle.top,
            (std::max)(admitted.top, assembled.top));
        triangle.right = (std::min)(triangle.right,
            (std::min)(admitted.right, assembled.right));
        triangle.bottom = (std::min)(triangle.bottom,
            (std::min)(admitted.bottom, assembled.bottom));
        return triangle.right > triangle.left &&
               triangle.bottom > triangle.top;
    };
    // Remember only source IA indices whose actual clipped polygons can
    // color the admitted game scissor. This 16 KiB stack index table avoids
    // a second 8192-triangle projection pass and never stores fake pixels.
    // 8192 is the fail-closed upper bound already proved above.
    std::array<std::uint16_t, 8192u> visibleIndices{};
    std::size_t visibleCount = 0u;
    for (std::size_t t = 0u; t < count; ++t) {
        NativeRawDrawExtent triangle{};
        if (projected_triangle(t, triangle))
            visibleIndices[visibleCount++] = static_cast<std::uint16_t>(t);
    }
    if (!visibleCount) return false;
    bool found = false;
    NativeRawDrawExtent firstWindow{};
    NativeRawDualTile firstSampled{};
    // Rotate across VISIBLE source primitives, not raw IA count: when
    // nearly every menu/race triangle is offscreen, ordinal % count
    // repeatedly selected the same surviving island. The actual native
    // GPU capture must visit all visible source islands before advancing
    // the within-triangle pixel sweep.
    const std::size_t start = static_cast<std::size_t>(ordinal) % visibleCount;
    for (std::size_t step = 0u; step < visibleCount; ++step) {
        const auto t = static_cast<std::size_t>(
            visibleIndices[(start + step) % visibleCount]);
        NativeRawDrawExtent triangle{};
        NativeRawFvfInteriorSample interior{};
        if (!projected_triangle(t, triangle, &interior)) return false;
        // Revisit each original source triangle on its own genuine GPU
        // readback grid. Previously every island used ordinal=0, so even
        // hundreds of captured menu/car/race Draws sampled the SAME corner
        // of each large primitive and permanently missed its inner pixels.
        // A complete pass through visible source triangles advances one sample
        // cell within EACH triangle, without projecting any synthetic RGB.
        NativeRawDualTile sampled{};
        const auto sourcePhase =
            static_cast<std::uint32_t>(ordinal / visibleCount);
        if (!native_raw_swept_dual_draw_tile(
                sw, sh, tw, th, triangle, sourcePhase, sampled))
            continue;
        // For sparse diagonal menu/race FVF geometry the bounding-box
        // sweep can miss the actual filled polygon entirely. Sample two
        // distinct authentic clipped-polygon interior points on the first
        // two phases of each eight-pass cycle, then continue the original
        // complete source GPU sweep. Both copies belong to the SAME actual
        // D3D11 Draw; no CPU-generated RGB or full-frame promotion.
        // Staging copies still use only the REAL native GPU PRE/POST images.
        if (interior.sparseDiagonal && (sourcePhase % 8u) < 2u) {
            const auto clampOrigin = [](std::int64_t p,
                std::uint32_t size, std::uint32_t extent) noexcept {
                return static_cast<std::uint32_t>((std::max)(
                    std::int64_t{0}, (std::min)(
                        p - static_cast<std::int64_t>(size) / 2,
                        static_cast<std::int64_t>(extent - size))));
            };
            const NativeRawTileOrigin centered{
                clampOrigin(interior.pixelX, tw, sw),
                clampOrigin(interior.pixelY, th, sh)};
            const NativeRawTileOrigin alternate{
                clampOrigin(interior.alternatePixelX, tw, sw),
                clampOrigin(interior.alternatePixelY, th, sh)};
            const NativeRawDualTile swept = sampled;
            const bool alternateFirst = (sourcePhase % 8u) == 1u;
            sampled.first = alternateFirst ? alternate : centered;
            sampled.hasSecond = false;
            const auto companion = alternateFirst ? centered : alternate;
            if (native_raw_source_tiles_disjoint(
                    sampled.first, companion, tw, th)) {
                sampled.second = companion;
                sampled.hasSecond = true;
            } else if (native_raw_source_tiles_disjoint(
                           sampled.first, swept.first, tw, th)) {
                sampled.second = swept.first;
                sampled.hasSecond = true;
            } else if (swept.hasSecond &&
                       native_raw_source_tiles_disjoint(
                           sampled.first, swept.second, tw, th)) {
                sampled.second = swept.second;
                sampled.hasSecond = true;
            }
        }
        if (!found) {
            out.first = sampled.first;
            firstWindow = triangle;
            firstSampled = sampled;
            found = true;
        } else {
            // Prefer independent primitive islands. A large later triangle
            // may have its first crop overlapping ours but a second genuine
            // source crop that is physically disjoint; inspect both.
            if (native_raw_source_tiles_disjoint(
                    out.first, sampled.first, tw, th)) {
                out.second = sampled.first;
                out.hasSecond = true;
                return true;
            }
            if (sampled.hasSecond &&
                native_raw_source_tiles_disjoint(
                    out.first, sampled.second, tw, th)) {
                out.second = sampled.second;
                out.hasSecond = true;
                return true;
            }
        }
    }
    if (!found) return false;
    // With one visible primitive, the sparse polygon-interior tile can
    // replace the first swept GPU copy. Preserve the companion selected
    // alongside that REAL source crop; it may contain independent menu/race
    // RGB outside the 512x288 interior capture. The old fallback silently
    // threw this copy away and used the sweep's SECOND tile, which could
    // overlap the newly centered FIRST tile.
    if (firstSampled.hasSecond &&
        native_raw_source_tiles_disjoint(
            out.first, firstSampled.second, tw, th)) {
        out.second = firstSampled.second;
        out.hasSecond = true;
        return true;
    }
    // A non-sparse primitive or a narrow scissor can still have a second
    // genuine swept GPU crop. Test BOTH physical candidates relative to
    // the ACTUAL selected first tile, not relative to the sweep's discarded
    // first tile. Never advertise overlapping PRE/POST GPU regions as
    // independent evidence; one valid tile remains useful.
    NativeRawDualTile within{};
    if (native_raw_swept_dual_draw_tile(
            sw, sh, tw, th, firstWindow,
            static_cast<std::uint32_t>(ordinal / visibleCount), within)) {
        if (native_raw_source_tiles_disjoint(
                out.first, within.first, tw, th)) {
            out.second = within.first;
            out.hasSecond = true;
        } else if (within.hasSecond &&
                   native_raw_source_tiles_disjoint(
                       out.first, within.second, tw, th)) {
            out.second = within.second;
            out.hasSecond = true;
        }
    }
    return true;
}
} // namespace outrun::vr::dx11
