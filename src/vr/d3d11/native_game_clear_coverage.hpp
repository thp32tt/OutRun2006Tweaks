#pragma once
#include <array>
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 clips Clear D3DRECTs to the viewport. Preserve full-size native
// backbuffer color/depth seeds when game-authored Clear rectangles extend
// beyond the physical target, but never accept a gap after clipping.
struct GameNativeClearCoverage {
    template<typename Rect>
    [[nodiscard]] static constexpr bool covers_whole(
        std::uint32_t w, std::uint32_t h,
        std::uint32_t vx, std::uint32_t vy,
        std::uint32_t vw, std::uint32_t vh,
        std::uint32_t count, const Rect* rects) noexcept {
        if (!w || !h || w > 0x7fffffffU || h > 0x7fffffffU ||
            vx != 0u || vy != 0u || vw != w || vh != h) return false;
        if (count == 0u) return true; // D3D9 ignores pRects when Count==0.
        if (!rects || count > 16u) return false;
        struct ClippedRect {
            std::int64_t x1, y1, x2, y2;
        };
        std::array<ClippedRect, 16u> clipped{};
        std::uint32_t validCount = 0u;
        const auto clamp = [](std::int64_t coordinate, std::int64_t extent) constexpr {
            return coordinate < 0 ? std::int64_t{0} :
                coordinate > extent ? extent : coordinate;
        };
        for (std::uint32_t i = 0u; i < count; ++i) {
            const auto& r = rects[i];
            // Reversed source extents are ambiguous even if another Clear
            // rectangle covers the surface: reject rather than infer pixels.
            if (r.x1 >= r.x2 || r.y1 >= r.y2) return false;
            const ClippedRect c{
                clamp(static_cast<std::int64_t>(r.x1), w),
                clamp(static_cast<std::int64_t>(r.y1), h),
                clamp(static_cast<std::int64_t>(r.x2), w),
                clamp(static_cast<std::int64_t>(r.y2), h)};
            // A wholly outside rectangle writes nothing in D3D9.
            if (c.x1 >= c.x2 || c.y1 >= c.y2) continue;
            clipped[validCount++] = c;
        }
        if (validCount == 0u) return false;
        // Sweep clipped Y bands, then merge overlapping/touching X intervals.
        // This verifies the actual union rather than trusting a bounding box.
        std::int64_t y = 0;
        while (y < h) {
            std::int64_t nextY = h;
            for (std::uint32_t i = 0; i < validCount; ++i) {
                const auto& r = clipped[i];
                if (r.y1 > y && r.y1 < nextY) nextY = r.y1;
                if (r.y2 > y && r.y2 < nextY) nextY = r.y2;
            }
            std::int64_t x = 0;
            while (x < w) {
                std::int64_t nextX = x;
                for (std::uint32_t i = 0; i < validCount; ++i) {
                    const auto& r = clipped[i];
                    if (r.y1 <= y && r.y2 >= nextY &&
                        r.x1 <= x && r.x2 > nextX)
                        nextX = r.x2;
                }
                if (nextX == x) return false;
                x = nextX;
            }
            y = nextY;
        }
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
