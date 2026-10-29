#pragma once
// Position opt-in GPU diagnostic tiles inside the authenticated native
// Draw raster extent. This admits no game Draw or full-frame publication.
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace outrun::vr::dx11 {
struct NativeRawDrawExtent { std::int64_t left{},top{},right{},bottom{}; };
struct NativeRawTileOrigin { std::uint32_t x{},y{}; };
// D3D11 viewports are fractional. Truncating BOTH edges inward loses
// authentic GPU-covered pixels at tiny menu, HUD and race viewport edges.
// Quantize outward only AFTER checking source identity/finite dimensions;
// scissor intersection remains owned by the caller. No pixel is fabricated.
[[nodiscard]] inline bool native_raw_viewport_pixel_extent(
    std::uint32_t targetWidth, std::uint32_t targetHeight,
    float x, float y, float width, float height,
    NativeRawDrawExtent& out) noexcept {
    out = {};
    if (!targetWidth || !targetHeight || !std::isfinite(x) ||
        !std::isfinite(y) || !std::isfinite(width) ||
        !std::isfinite(height) || !(width > 0.0f) ||
        !(height > 0.0f)) return false;
    const double left = static_cast<double>(x);
    const double top = static_cast<double>(y);
    const double right = left + static_cast<double>(width);
    const double bottom = top + static_cast<double>(height);
    const auto clip = [](double coordinate, double limit) noexcept {
        return (std::max)(0.0, (std::min)(coordinate, limit));
    };
    const double l = clip(left, targetWidth), t = clip(top, targetHeight);
    const double r = clip(right, targetWidth), b = clip(bottom, targetHeight);
    if (!(r > l) || !(b > t)) return false;
    out = {static_cast<std::int64_t>(std::floor(l)),
           static_cast<std::int64_t>(std::floor(t)),
           static_cast<std::int64_t>(std::ceil(r)),
           static_cast<std::int64_t>(std::ceil(b))};
    return out.right > out.left && out.bottom > out.top;
}
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
