#pragma once
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11::live_game_frame {
// D3D9 Clear clips its supplied D3DRECTs to the viewport. Recreate only
// real complete game backbuffer Clears; otherwise native output is invalid.
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
        for (std::uint32_t i=0; i<count; ++i) {
            const auto& r=rects[i];
            if (r.x1 < 0 || r.y1 < 0 || r.x1 >= r.x2 || r.y1 >= r.y2 ||
                static_cast<std::uint64_t>(r.x2)>w ||
                static_cast<std::uint64_t>(r.y2)>h) return false;
        }
        // Verify tiled horizontal/vertical Clears by sweeping each Y band.
        // The rightmost reachable X must cover the entire band (no holes).
        std::int64_t y=0;
        while (y<h) {
            std::int64_t nextY=h;
            for (std::uint32_t i=0; i<count; ++i) {
                if (rects[i].y1>y && rects[i].y1<nextY) nextY=rects[i].y1;
                if (rects[i].y2>y && rects[i].y2<nextY) nextY=rects[i].y2;
            }
            std::int64_t x=0;
            while (x<w) {
                std::int64_t nextX=x;
                for (std::uint32_t i=0; i<count; ++i) {
                    const auto& r=rects[i];
                    if (r.y1<=y && r.y2>=nextY && r.x1<=x && r.x2>nextX)
                        nextX=r.x2;
                }
                if (nextX==x) return false;
                x=nextX;
            }
            y=nextY;
        }
        return true;
    }
};
} // namespace outrun::vr::dx11::live_game_frame
