#pragma once
// Authentic D3D9 Present source-crop coverage for the opt-in native GPU tile.
// The caller verifies each dirty rectangle's bounds and union; a populated
// dirty-region pointer alone is NOT evidence that the game will present our
// overlay. Do not use this for full native frame or stereo publication.
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_raw_preview_present_coverage(
    bool hasDirtyRegion, bool fullBackbufferCovered,
    bool sourceCropCovered, bool sourceCropPartitionCovered) noexcept {
    return !hasDirtyRegion || fullBackbufferCovered ||
           sourceCropCovered || sourceCropPartitionCovered;
}

} // namespace outrun::vr::dx11

// A D3D9 Present may repaint only a small menu/car/race dirty subset.
// In RAW mode, check the ACTUAL selected diagnostic destination tile rather
// than requiring the full game crop to be dirty. This grants no full-frame
// or OpenXR publication and cannot accept a bounding RECT with holes.
#include <algorithm>
#include <cstdint>
#include <limits>
#include "native_game_raw_partial_present_tile.hpp"
namespace outrun::vr::dx11 {
struct NativeRawPresentDirtyRect {
    std::int64_t left{}, top{}, right{}, bottom{};
};
struct NativeRawPresentDirtyRegion {
    static constexpr std::uint32_t kMaxRects = 32u;
    bool headerVerified = false;
    std::uint32_t count{};
    std::int64_t boundLeft{}, boundTop{}, boundRight{}, boundBottom{};
    NativeRawPresentDirtyRect rectangles[kMaxRects]{};
};
[[nodiscard]] constexpr bool native_raw_dirty_region_covers_tile(
    std::uint32_t backWidth, std::uint32_t backHeight,
    const NativeRawPresentDirtyRegion& region,
    const NativeRawPresentTile& tile) noexcept {
    constexpr auto kMax = static_cast<std::uint32_t>(
        (std::numeric_limits<std::int32_t>::max)());
    if (!region.headerVerified || region.count == 0u ||
        region.count > NativeRawPresentDirtyRegion::kMaxRects ||
        !backWidth || !backHeight || backWidth > kMax || backHeight > kMax ||
        tile.copyWidth == 0u || tile.copyHeight == 0u ||
        tile.copyWidth > backWidth || tile.copyHeight > backHeight ||
        tile.destinationX < 0 || tile.destinationY < 0 ||
        tile.destinationX > static_cast<std::int64_t>(backWidth - tile.copyWidth) ||
        tile.destinationY > static_cast<std::int64_t>(backHeight - tile.copyHeight) ||
        region.boundLeft < 0 || region.boundTop < 0 ||
        region.boundRight <= region.boundLeft ||
        region.boundBottom <= region.boundTop ||
        region.boundRight > backWidth || region.boundBottom > backHeight)
        return false;
    std::int64_t minX = backWidth, minY = backHeight, maxX = 0, maxY = 0;
    for (std::uint32_t i = 0u; i < region.count; ++i) {
        const auto& r = region.rectangles[i];
        if (r.left < 0 || r.top < 0 || r.right <= r.left ||
            r.bottom <= r.top || r.right > backWidth || r.bottom > backHeight)
            return false;
        if (r.left < minX) minX = r.left;
        if (r.top < minY) minY = r.top;
        if (r.right > maxX) maxX = r.right;
        if (r.bottom > maxY) maxY = r.bottom;
    }
    // Validate rcBound against the actual rectangle population. A forged
    // full-crop bounding box alone must never authorize a RAW pixel upload.
    if (minX != region.boundLeft || minY != region.boundTop ||
        maxX != region.boundRight || maxY != region.boundBottom)
        return false;
    const auto right = tile.destinationX + tile.copyWidth;
    const auto bottom = tile.destinationY + tile.copyHeight;
    std::int64_t x = tile.destinationX;
    while (x < right) {
        std::int64_t nextX = right;
        for (std::uint32_t i = 0u; i < region.count; ++i) {
            const auto& r = region.rectangles[i];
            if (r.left > x && r.left < nextX) nextX = r.left;
            if (r.right > x && r.right < nextX) nextX = r.right;
        }
        if (nextX <= x) return false;
        std::int64_t y = tile.destinationY;
        for (std::uint32_t step = 0u; step < region.count && y < bottom; ++step) {
            std::int64_t reach = y;
            for (std::uint32_t i = 0u; i < region.count; ++i) {
                const auto& r = region.rectangles[i];
                if (r.left <= x && r.right >= nextX &&
                    r.top <= y && r.bottom > reach)
                    reach = r.bottom < bottom ? r.bottom : bottom;
            }
            if (reach == y) return false;
            y = reach;
        }
        if (y != bottom) return false;
        x = nextX;
    }
    return true;
}
// Allow two independently captured native Draw images in separate ORIGINAL
// game repaint islands, without overlapping either image or claiming a
// complete scene. Their pixel counts require identical tile dimensions.
[[nodiscard]] constexpr bool native_raw_disjoint_equal_tiles(
    const NativeRawPresentTile& a, const NativeRawPresentTile& b) noexcept {
    if (!a.copyWidth || !a.copyHeight ||
        a.copyWidth != b.copyWidth || a.copyHeight != b.copyHeight)
        return false;
    return a.destinationX + std::int64_t{a.copyWidth} <= b.destinationX ||
           b.destinationX + std::int64_t{b.copyWidth} <= a.destinationX ||
           a.destinationY + std::int64_t{a.copyHeight} <= b.destinationY ||
           b.destinationY + std::int64_t{b.copyHeight} <= a.destinationY;
}
 // When a D3D9 menu/car Present updates only a subset, the default
 // top-right RAW diagnostic tile may be outside ALL genuine dirty pixels.
 // Keep it when fully covered; otherwise find the largest tile inside a
 // real intersecting dirty rectangle. Never expand the game's repaint.
 [[nodiscard]] constexpr bool native_raw_dirty_region_place_tile(
     std::uint32_t backWidth, std::uint32_t backHeight,
     std::int64_t cropLeft, std::int64_t cropTop,
     std::int64_t cropRight, std::int64_t cropBottom,
     const NativeRawPresentDirtyRegion& dirty,
     std::uint32_t sourceWidth, std::uint32_t sourceHeight,
     NativeRawPresentTile& placed,
     const NativeRawPresentTile* exclude = nullptr) noexcept {
     placed = {};
     // Only an authenticated first image may reserve painted D3D9 pixels.
     if (exclude && !native_raw_dirty_region_covers_tile(
             backWidth, backHeight, dirty, *exclude)) return false;
     NativeRawPresentTile ordinary{};
     if (!native_raw_partial_present_tile(
             backWidth, backHeight, cropLeft, cropTop,
             cropRight, cropBottom, sourceWidth, sourceHeight, ordinary))
         return false;
     if ((!exclude || native_raw_disjoint_equal_tiles(ordinary, *exclude)) &&
         native_raw_dirty_region_covers_tile(
             backWidth, backHeight, dirty, ordinary)) {
         placed = ordinary;
         return true;
     }
     // Each candidate is verified against the WHOLE bounded region, not
     // against rcBound or merely an intersecting rectangle. A malformed
     // member anywhere in the region prevents publication.
     bool found = false;
     std::uint64_t largestArea = 0u;
     // D3D9 RGNDATA can split one repainted menu area into several
     // adjacent rectangles. The individual rectangles may each be too
     // small for a 24x24 RAW crop even when their authenticated UNION is
     // sufficient. The candidate is NEVER trusted just because its
     // bounding box intersects the Present: check every painted pixel
     // through native_raw_dirty_region_covers_tile before accepting it.
     const auto consider = [&](std::int64_t left, std::int64_t top,
                               std::int64_t right,
                               std::int64_t bottom) noexcept {
         NativeRawPresentTile candidate{};
         if (!native_raw_partial_present_tile(
                 backWidth, backHeight, left, top, right, bottom,
                 sourceWidth, sourceHeight, candidate))
             return;
         const auto area = std::uint64_t{candidate.copyWidth} *
                           candidate.copyHeight;
         if ((found && area <= largestArea) ||
             (exclude && !native_raw_disjoint_equal_tiles(candidate, *exclude)) ||
             !native_raw_dirty_region_covers_tile(
                 backWidth, backHeight, dirty, candidate))
             return;
         found = true;
         largestArea = area;
         placed = candidate;
     };
     // Fast path for a complete, possibly fragmented source repaint.
     // A forged rcBound, gap or out-of-bounds member fails the union test.
     consider((std::max)(cropLeft, dirty.boundLeft),
              (std::max)(cropTop, dirty.boundTop),
              (std::min)(cropRight, dirty.boundRight),
              (std::min)(cropBottom, dirty.boundBottom));
     for (std::uint32_t i = 0u;
          i < dirty.count && i < NativeRawPresentDirtyRegion::kMaxRects; ++i) {
         const auto& rect = dirty.rectangles[i];
         consider((std::max)(cropLeft, rect.left),
                  (std::max)(cropTop, rect.top),
                  (std::min)(cropRight, rect.right),
                  (std::min)(cropBottom, rect.bottom));
     }
     // RGNDATA may fragment a genuine menu/car repaint into more than
     // two adjoining pieces (including >8 total members with outliers).
     // Enumerating pairs misses a valid native GPU tile in that case.
     // Discover each edge/overlap-connected repaint component in a bounded
     // flood fill (at most 32 rectangles and 32*32 adjacency probes overall).
     // The component bounds only propose a location: every candidate still
     // requires strict ORIGINAL full-region bounds and per-pixel union proof.
     // A gap, malformed member, or fabricated rcBound never earns coverage.
     if (!dirty.headerVerified || dirty.count == 0u ||
         dirty.count > NativeRawPresentDirtyRegion::kMaxRects)
         return false;
     bool visited[NativeRawPresentDirtyRegion::kMaxRects]{};
     for (std::uint32_t seed = 0u; seed < dirty.count; ++seed) {
         if (visited[seed]) continue;
         std::uint32_t queue[NativeRawPresentDirtyRegion::kMaxRects]{};
         std::uint32_t read = 0u, size = 1u;
         queue[0] = seed;
         visited[seed] = true;
         auto componentLeft = dirty.rectangles[seed].left;
         auto componentTop = dirty.rectangles[seed].top;
         auto componentRight = dirty.rectangles[seed].right;
         auto componentBottom = dirty.rectangles[seed].bottom;
         while (read < size) {
             const auto& current = dirty.rectangles[queue[read++]];
             for (std::uint32_t i = 0u; i < dirty.count; ++i) {
                 if (visited[i]) continue;
                 const auto& next = dirty.rectangles[i];
                 // Touching edges are contiguous D3D9 source pixels; a
                 // shared corner may widen bounds but cannot pass the
                 // independent exact per-pixel coverage test if hollow.
                 if (next.left > current.right ||
                     next.right < current.left ||
                     next.top > current.bottom ||
                     next.bottom < current.top)
                     continue;
                 visited[i] = true;
                 queue[size++] = i; // each source member enqueued once
                 componentLeft = (std::min)(componentLeft, next.left);
                 componentTop = (std::min)(componentTop, next.top);
                 componentRight = (std::max)(componentRight, next.right);
                 componentBottom = (std::max)(componentBottom, next.bottom);
             }
         }
         consider((std::max)(cropLeft, componentLeft),
                  (std::max)(cropTop, componentTop),
                  (std::min)(cropRight, componentRight),
                  (std::min)(cropBottom, componentBottom));
     }
     if (found) return true;
     // A connected component can be nonrectangular: e.g. three thin menu
     // strips make a real 48x48 island with an 8px-high attached tail.
     // Its full bounds place the RAW tile in the tail's unpainted neighbor,
     // and no single member is wide enough. Sweep source-authored Y edges
     // instead. Only members covering the ENTIRE band contribute X spans;
     // merging touching spans produces genuine rectangular repaint areas.
     // This is a fallback only, bounded by the original 32-member RGNDATA.
     for (std::uint32_t topIndex = 0u; topIndex < dirty.count; ++topIndex) {
         const auto top = (std::max)(cropTop, dirty.rectangles[topIndex].top);
         bool duplicateTop = false;
         for (std::uint32_t i = 0u; i < topIndex; ++i)
             if ((std::max)(cropTop, dirty.rectangles[i].top) == top)
                 duplicateTop = true;
         if (duplicateTop) continue;
         for (std::uint32_t bottomIndex = 0u;
              bottomIndex < dirty.count; ++bottomIndex) {
             const auto bottom = (std::min)(
                 cropBottom, dirty.rectangles[bottomIndex].bottom);
             // Retain the existing 24px image + two 8px label margins.
             if (bottom - top < 40) continue;
             bool duplicateBottom = false;
             for (std::uint32_t i = 0u; i < bottomIndex; ++i)
                 if ((std::min)(cropBottom, dirty.rectangles[i].bottom) == bottom)
                     duplicateBottom = true;
             if (duplicateBottom) continue;
             NativeRawPresentDirtyRect spans[NativeRawPresentDirtyRegion::kMaxRects]{};
             std::uint32_t count = 0u;
             for (std::uint32_t i = 0u; i < dirty.count; ++i) {
                 const auto& rect = dirty.rectangles[i];
                 if (rect.top > top || rect.bottom < bottom) continue;
                 const auto left = (std::max)(cropLeft, rect.left);
                 const auto right = (std::min)(cropRight, rect.right);
                 if (left >= right) continue;
                 std::uint32_t slot = count++;
                 while (slot && spans[slot - 1u].left > left) {
                     spans[slot] = spans[slot - 1u];
                     --slot;
                 }
                 spans[slot] = {left, top, right, bottom};
             }
             if (!count) continue;
             auto left = spans[0].left, right = spans[0].right;
             for (std::uint32_t i = 1u; i <= count; ++i) {
                 if (i < count && spans[i].left <= right) {
                     right = (std::max)(right, spans[i].right);
                     continue;
                 }
                 // Still authenticate against the ORIGINAL region, including
                 // all outliers and rcBound; sweep proposals grant no trust.
                 consider(left, top, right, bottom);
                 if (i < count) {
                     left = spans[i].left;
                     right = spans[i].right;
                 }
             }
         }
     }
     // The dual case is common in original D3D9 RGNDATA: a menu/car
     // repaint is sliced into short HORIZONTAL rows. None spans the
     // complete Y band above, and an attached rightward tail invalidates
     // the whole connected-component candidate. Sweep source-authored
     // X boundaries and merge vertically touching intervals instead.
     // This changes placement only in explicit RAW opt-in diagnostics.
     for (std::uint32_t leftIndex = 0u; leftIndex < dirty.count; ++leftIndex) {
         const auto left = (std::max)(cropLeft, dirty.rectangles[leftIndex].left);
         bool duplicateLeft = false;
         for (std::uint32_t i = 0u; i < leftIndex; ++i)
             if ((std::max)(cropLeft, dirty.rectangles[i].left) == left)
                 duplicateLeft = true;
         if (duplicateLeft) continue;
         for (std::uint32_t rightIndex = 0u;
              rightIndex < dirty.count; ++rightIndex) {
             const auto right = (std::min)(
                 cropRight, dirty.rectangles[rightIndex].right);
             // The native crop needs 24 source pixels plus two 8px margins.
             if (right - left < 40) continue;
             bool duplicateRight = false;
             for (std::uint32_t i = 0u; i < rightIndex; ++i)
                 if ((std::min)(cropRight, dirty.rectangles[i].right) == right)
                     duplicateRight = true;
             if (duplicateRight) continue;
             NativeRawPresentDirtyRect spans[NativeRawPresentDirtyRegion::kMaxRects]{};
             std::uint32_t count = 0u;
             for (std::uint32_t i = 0u; i < dirty.count; ++i) {
                 const auto& rect = dirty.rectangles[i];
                 if (rect.left > left || rect.right < right) continue;
                 const auto top = (std::max)(cropTop, rect.top);
                 const auto bottom = (std::min)(cropBottom, rect.bottom);
                 if (top >= bottom) continue;
                 std::uint32_t slot = count++;
                 while (slot && spans[slot - 1u].top > top) {
                     spans[slot] = spans[slot - 1u];
                     --slot;
                 }
                 spans[slot] = {left, top, right, bottom};
             }
             if (!count) continue;
             auto top = spans[0].top, bottom = spans[0].bottom;
             for (std::uint32_t i = 1u; i <= count; ++i) {
                 if (i < count && spans[i].top <= bottom) {
                     bottom = (std::max)(bottom, spans[i].bottom);
                     continue;
                 }
                 // These intervals are only CANDIDATES. Authentic D3D9
                 // bounds and every source-painted pixel are independently
                 // rechecked before the first GPU RGB byte is displayed.
                 consider(left, top, right, bottom);
                 if (i < count) {
                     top = spans[i].top;
                     bottom = spans[i].bottom;
                 }
             }
         }
     }
     return found;
 }
} // namespace outrun::vr::dx11

