#pragma once
// Position opt-in GPU diagnostic tiles inside the authenticated native
// Draw raster extent. This admits no game Draw or full-frame publication.
#include <algorithm>
#include <cstdint>
namespace outrun::vr::dx11 {
struct NativeRawDrawExtent { std::int64_t left{},top{},right{},bottom{}; };
struct NativeRawTileOrigin { std::uint32_t x{},y{}; };
[[nodiscard]] constexpr bool native_raw_draw_tile(
    std::uint32_t sw, std::uint32_t sh, std::uint32_t tw, std::uint32_t th,
    NativeRawDrawExtent bounds, std::uint32_t ordinal,
    NativeRawTileOrigin& out) noexcept {
    out = {};
    if (!tw || !th || sw < tw || sh < th) return false;
    const auto l=(std::max)(std::int64_t{0},bounds.left);
    const auto t=(std::max)(std::int64_t{0},bounds.top);
    const auto r=(std::min)(std::int64_t{sw},bounds.right);
    const auto b=(std::min)(std::int64_t{sh},bounds.bottom);
    if(l>=r || t>=b) return false;
    auto x=l+(r-l)/2, y=t+(b-t)/2;
    switch(ordinal%5u) {
    case 1u: x=l; y=t; break;
    case 2u: x=r-1; y=t; break;
    case 3u: x=l; y=b-1; break;
    case 4u: x=r-1; y=b-1; break;
    default: break;
    }
    out.x=static_cast<std::uint32_t>((std::max)(std::int64_t{0},
        (std::min)(x-std::int64_t{tw}/2,std::int64_t{sw-tw})));
    out.y=static_cast<std::uint32_t>((std::max)(std::int64_t{0},
        (std::min)(y-std::int64_t{th}/2,std::int64_t{sh-th})));
    return true;
}
} // namespace outrun::vr::dx11
