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
     NativeRawPresentTile& placed) noexcept {
     placed = {};
     NativeRawPresentTile ordinary{};
     if (!native_raw_partial_present_tile(
             backWidth, backHeight, cropLeft, cropTop,
             cropRight, cropBottom, sourceWidth, sourceHeight, ordinary))
         return false;
     if (native_raw_dirty_region_covers_tile(
             backWidth, backHeight, dirty, ordinary)) {
         placed = ordinary;
         return true;
     }
     // Each candidate is verified against the WHOLE bounded region, not
     // against rcBound or merely an intersecting rectangle. A malformed
     // member anywhere in the region prevents publication.
     bool found = false;
     std::uint64_t largestArea = 0u;
     for (std::uint32_t i = 0u;
          i < dirty.count && i < NativeRawPresentDirtyRegion::kMaxRects; ++i) {
         const auto& rect = dirty.rectangles[i];
         const auto left = (std::max)(cropLeft, rect.left);
         const auto top = (std::max)(cropTop, rect.top);
         const auto right = (std::min)(cropRight, rect.right);
         const auto bottom = (std::min)(cropBottom, rect.bottom);
         NativeRawPresentTile candidate{};
         if (!native_raw_partial_present_tile(
                 backWidth, backHeight, left, top, right, bottom,
                 sourceWidth, sourceHeight, candidate) ||
             !native_raw_dirty_region_covers_tile(
                 backWidth, backHeight, dirty, candidate))
             continue;
         const auto area = std::uint64_t{candidate.copyWidth} *
                           candidate.copyHeight;
         if (!found || area > largestArea) {
             found = true;
             largestArea = area;
             placed = candidate;
         }
     }
     return found;
 }
} // namespace outrun::vr::dx11
