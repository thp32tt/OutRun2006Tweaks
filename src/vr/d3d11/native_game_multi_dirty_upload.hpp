#pragma once
#include "native_game_dirty_region.hpp"
#include "native_game_present_region.hpp"
#include <array>
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// A partially dirty D3D9 Present may contain several disjoint updates.
// Admit up to 32 verified, nonoverlapping rectangles; clip each to the
// current visible source and keep every untouched D3D9 pixel authoritative.
struct GameNativeMultiDirtySelection {
    std::array<GameNativePresentRegion, GameNativeDirtyRegionCoverage::kMaxPartitionRects> regions{};
    std::uint32_t count = 0u;
    // Single atomic D3D9 upload spans all verified tiles. The untouched
    // holes must be seeded from the current original game backbuffer first.
    GameNativePresentRegion uploadBounds{};
    bool valid = false;
};
struct GameNativeMultiDirtyUpload {
    [[nodiscard]] static constexpr GameNativeMultiDirtySelection select(
        std::uint32_t width, std::uint32_t height,
        GameNativePresentRegion visible,
        std::uint32_t rectangleCount, std::uint32_t bufferBytes,
        std::int64_t boundLeft, std::int64_t boundTop,
        std::int64_t boundRight, std::int64_t boundBottom,
        const GameNativeDirtyRectangle* rects,
        bool allowOverlap = false) noexcept {
        GameNativeMultiDirtySelection out{};
        if (!rects || !visible.full_frame_placement(width, height, width, height).valid ||
            rectangleCount < 2u || rectangleCount > GameNativeDirtyRegionCoverage::kMaxPartitionRects ||
            bufferBytes < rectangleCount * 16u) return {};
        std::int64_t minX = (std::numeric_limits<std::int64_t>::max)();
        std::int64_t minY = (std::numeric_limits<std::int64_t>::max)();
        std::int64_t maxX = 0, maxY = 0;
        for (std::uint32_t i = 0u; i < rectangleCount; ++i) {
            const auto& r = rects[i];
            if (r.left < 0 || r.top < 0 || r.right <= r.left || r.bottom <= r.top ||
                r.right > static_cast<std::int64_t>(width) ||
                r.bottom > static_cast<std::int64_t>(height)) return {};
            // Full-coverage callers reject overlapping rectangles by default.
            // Actual partial Present can copy intersecting tiles from the same
            // native game frame into one backbuffer-seeded atomic upload.
            if (!allowOverlap) {
                for (std::uint32_t j = 0u; j < i; ++j) {
                    const auto& p = rects[j];
                    if (r.left < p.right && p.left < r.right &&
                        r.top < p.bottom && p.top < r.bottom) return {};
                }
            }
            if (r.left < minX) minX = r.left;
            if (r.top < minY) minY = r.top;
            if (r.right > maxX) maxX = r.right;
            if (r.bottom > maxY) maxY = r.bottom;
            const std::int64_t left = r.left > visible.left ? r.left : visible.left;
            const std::int64_t top = r.top > visible.top ? r.top : visible.top;
            const std::int64_t right = r.right < visible.right ? r.right : visible.right;
            const std::int64_t bottom = r.bottom < visible.bottom ? r.bottom : visible.bottom;
            if (left < right && top < bottom)
                out.regions[out.count++] = {left, top, right, bottom};
        }
        if (minX != boundLeft || minY != boundTop ||
            maxX != boundRight || maxY != boundBottom || !out.count) return {};
        std::int64_t uploadLeft = out.regions[0].left;
        std::int64_t uploadTop = out.regions[0].top;
        std::int64_t uploadRight = out.regions[0].right;
        std::int64_t uploadBottom = out.regions[0].bottom;
        for (std::uint32_t i = 1u; i < out.count; ++i) {
            const auto& tile = out.regions[i];
            if (tile.left < uploadLeft) uploadLeft = tile.left;
            if (tile.top < uploadTop) uploadTop = tile.top;
            if (tile.right > uploadRight) uploadRight = tile.right;
            if (tile.bottom > uploadBottom) uploadBottom = tile.bottom;
        }
        out.uploadBounds = {uploadLeft, uploadTop, uploadRight, uploadBottom};
        out.valid = true;
        return out;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
