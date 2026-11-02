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
    NativeRawFvfInteriorSample firstInterior{};
    // Rotate across VISIBLE source primitives, not raw IA count: when
    // nearly every menu/race triangle is offscreen, ordinal % count
    // repeatedly selected the same surviving island. The actual native
    // GPU capture must visit all visible source islands before advancing
    // the within-triangle pixel sweep.
    const std::size_t start = static_cast<std::size_t>(ordinal) % visibleCount;
    // The same physical source-target clamp is used for sparse-primary
    // crops and independent polygon centers. This changes sampling ONLY:
    // native PRE/POST bytes, D3D9 scissor/RT identity and Present remain
    // mandatory before a real GPU pixel can be published.
    const auto origin = [&](std::int64_t x, std::int64_t y) noexcept {
        const auto clamp = [](std::int64_t p, std::uint32_t size,
                              std::uint32_t extent) noexcept {
            return static_cast<std::uint32_t>((std::max)(
                std::int64_t{0}, (std::min)(
                    p - static_cast<std::int64_t>(size) / 2,
                    static_cast<std::int64_t>(extent - size))));
        };
        return NativeRawTileOrigin{clamp(x, tw, sw), clamp(y, th, sh)};
    };
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
        // A sparse menu/race triangle may have almost no pixels in its
        // screen-wide AABB. In all eight source phases anchor the FIRST
        // actual D3D11 PRE/POST GPU copy inside the genuine clipped polygon:
        // center, two distant ends and their interior half-way positions.
        // The previous six AABB-only phases could repeatedly miss ALL RGB.
        // Preserve swept GPU cells as SECONDARY candidates and keep the
        // original D3D9 Present/source/epoch checks authoritative.
        if (interior.sparseDiagonal) {
            const NativeRawTileOrigin centered = origin(
                interior.pixelX, interior.pixelY);
            const NativeRawTileOrigin farEnd = origin(
                interior.alternatePixelX, interior.alternatePixelY);
            const NativeRawTileOrigin oppositeEnd = origin(
                interior.oppositePixelX, interior.oppositePixelY);
            const NativeRawTileOrigin middleFar = origin(
                interior.pixelX / 2 + interior.alternatePixelX / 2,
                interior.pixelY / 2 + interior.alternatePixelY / 2);
            const NativeRawTileOrigin middleOpposite = origin(
                interior.pixelX / 2 + interior.oppositePixelX / 2,
                interior.pixelY / 2 + interior.oppositePixelY / 2);
            const NativeRawTileOrigin anchors[8]{
                centered, farEnd, oppositeEnd, middleFar, middleOpposite,
                farEnd, oppositeEnd, centered};
            const auto phase = sourcePhase % 8u;
            const NativeRawDualTile swept = sampled;
            sampled.first = anchors[phase];
            sampled.hasSecond = false;
            // A second disjoint genuine polygon interior beats an AABB
            // corner; if none fits, keep the authentic GPU raster sweep.
            const NativeRawTileOrigin candidates[5]{
                phase == 0u ? farEnd : centered,
                phase == 1u ? centered : farEnd,
                oppositeEnd, swept.first, swept.second};
            for (std::size_t c = 0u; c < 5u; ++c) {
                if (c == 4u && !swept.hasSecond) break;
                if (!native_raw_source_tiles_disjoint(
                        sampled.first, candidates[c], tw, th)) continue;
                sampled.second = candidates[c];
                sampled.hasSecond = true;
                break;
            }
        }
        if (!found) {
            out.first = sampled.first;
            firstWindow = triangle;
            firstSampled = sampled;
            firstInterior = interior;
            found = true;
        } else {
            // A second broad menu/car/race primitive can fill the MIDDLE of
            // its clipped triangle but neither corner of its AABB sweep.
            // Anchor its second PRE/POST source crop at a point obtained from
            // that actual separately assembled/clipped primitive. This does
            // not infer RGB: the paired copies still come only from the
            // already-executed native D3D11 Draw, with the original source
            // target, epoch and GPU delta checks downstream.
            // Disjointness is physical, not inferred from primitive indices.
            const auto secondInterior = origin(interior.pixelX, interior.pixelY);
            if (native_raw_source_tiles_disjoint(
                    out.first, secondInterior, tw, th)) {
                out.second = secondInterior;
                out.hasSecond = true;
                return true;
            }
            // If both primitive centers overlap, preserve the independent
            // authentic GPU sweep before falling back to one source crop.
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
    // A large single menu/car/race triangle is not necessarily a filled
    // rectangle. Keep the original source-raster sweep as the FIRST native
    // PRE/POST capture for broad polygons, but choose a disjoint SECOND copy
    // from its genuinely clipped triangle interior before trying an AABB
    // corner. Otherwise both copies can sample empty triangle corners while
    // a real D3D11 Draw changes RGB in the unsampled polygon center.
    // This is still sampling only: actual GPU before/after deltas, original
    // game source RT/scissor and D3D9 Present remain required downstream.
    if (!firstInterior.sparseDiagonal) {
        const NativeRawTileOrigin polygonInterior[3]{
            origin(firstInterior.pixelX, firstInterior.pixelY),
            origin(firstInterior.alternatePixelX,
                   firstInterior.alternatePixelY),
            origin(firstInterior.oppositePixelX,
                   firstInterior.oppositePixelY)};
        // Rotate through independently projected real polygon interiors
        // on subsequent original Draws, retaining the sweep's complete
        // source-cell progression and deterministic stable ordering.
        const std::size_t phase =
            static_cast<std::size_t>(ordinal / visibleCount) % 3u;
        for (std::size_t step = 0u; step < 3u; ++step) {
            const auto candidate = polygonInterior[(phase + step) % 3u];
            if (!native_raw_source_tiles_disjoint(
                    out.first, candidate, tw, th)) continue;
            out.second = candidate;
            out.hasSecond = true;
            return true;
        }
    }
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
