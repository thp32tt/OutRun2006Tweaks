#pragma once
#include <cstdint>
#include <algorithm>
#include <cmath>
#include <cstddef>
namespace outrun::vr::dx11 {
struct NativeGameOffscreenColorKey {
    std::uintptr_t resource{};
    std::uint32_t arraySlice{}, mipSlice{};
};
// A real GPU copy of a different camera allocation, array eye or mip cannot
// inherit the current eye's offscreen game Draw color provenance.
[[nodiscard]] constexpr bool native_game_offscreen_color_key_matches(
    NativeGameOffscreenColorKey written,
    NativeGameOffscreenColorKey copied) noexcept {
    return written.resource != 0u && copied.resource != 0u &&
        written.resource == copied.resource &&
        written.arraySlice == copied.arraySlice &&
        written.mipSlice == copied.mipSlice;
}
static_assert(native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x1234u, 0u, 0u}));
static_assert(native_game_offscreen_color_key_matches(
    {0x1234u, 1u, 2u}, {0x1234u, 1u, 2u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x5678u, 0u, 0u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x1234u, 1u, 0u}));
static_assert(!native_game_offscreen_color_key_matches(
    {0x1234u, 0u, 0u}, {0x1234u, 0u, 1u}));
static_assert(!native_game_offscreen_color_key_matches(
    {}, {0x1234u, 0u, 0u}));

// Raster-clipped game camera Draws cannot authenticate copies of another
// untouched part of the SAME camera texture. Evidence follows the real GPU
// pixel region as well as resource, mip and array slice. Multiple separated
// Draw regions remain separate entries; never fill their bounding-box gap.
struct NativeGameOffscreenColorRegion {
    std::uint32_t left{}, top{}, right{}, bottom{};
};
[[nodiscard]] constexpr bool native_game_offscreen_color_region_valid(
    NativeGameOffscreenColorRegion r) noexcept {
    return r.left < r.right && r.top < r.bottom;
}
[[nodiscard]] constexpr bool native_game_offscreen_color_regions_intersect(
    NativeGameOffscreenColorRegion draw,
    NativeGameOffscreenColorRegion copied) noexcept {
    return native_game_offscreen_color_region_valid(draw) &&
        native_game_offscreen_color_region_valid(copied) &&
        draw.left < copied.right && copied.left < draw.right &&
        draw.top < copied.bottom && copied.top < draw.bottom;
}
// Viewports have fractional origins and extents. Record only source pixels
// whose centers are inside the current viewport/scissor and physical RTV;
// malformed / NaN raster state cannot supply provenance. This is intentionally
// conservative (MSAA edge-only coverage is not proof); native GPU commands
// still execute, with the original D3D9 renderer retained as fallback.
[[nodiscard]] inline NativeGameOffscreenColorRegion
native_game_offscreen_draw_pixel_region(
    std::uint32_t width, std::uint32_t height,
    double left, double top, double right, double bottom,
    bool scissorEnabled = false, std::int64_t scLeft = 0,
    std::int64_t scTop = 0, std::int64_t scRight = 0,
    std::int64_t scBottom = 0) noexcept {
    if (!width || !height ||
        !std::isfinite(left) || !std::isfinite(top) ||
        !std::isfinite(right) || !std::isfinite(bottom) ||
        right <= left || bottom <= top)
        return {};
    left = (std::max)(0.0, left);
    top = (std::max)(0.0, top);
    right = (std::min)(double(width), right);
    bottom = (std::min)(double(height), bottom);
    if (scissorEnabled) {
        left = (std::max)(left, double(scLeft));
        top = (std::max)(top, double(scTop));
        right = (std::min)(right, double(scRight));
        bottom = (std::min)(bottom, double(scBottom));
    }
    if (right <= left || bottom <= top) return {};
    const auto x0 = std::ceil(left - 0.5);
    const auto y0 = std::ceil(top - 0.5);
    const auto x1 = std::ceil(right - 0.5);
    const auto y1 = std::ceil(bottom - 0.5);
    if (x1 <= x0 || y1 <= y0) return {};
    return {std::uint32_t(x0), std::uint32_t(y0),
            std::uint32_t(x1), std::uint32_t(y1)};
}
static_assert(native_game_offscreen_color_regions_intersect(
    {0u, 0u, 200u, 100u}, {199u, 50u, 250u, 120u}));
static_assert(!native_game_offscreen_color_regions_intersect(
    {0u, 0u, 200u, 100u}, {200u, 50u, 250u, 120u}));
static_assert(!native_game_offscreen_color_regions_intersect(
    {0u, 0u, 200u, 100u}, {50u, 100u, 150u, 150u}));
static_assert(!native_game_offscreen_color_regions_intersect(
    {0u, 0u, 200u, 100u}, {0u, 0u, 0u, 50u}));
static_assert(!native_game_offscreen_color_regions_intersect(
    {}, {1u, 1u, 5u, 5u}));
// Disjoint camera viewports and mismatched postpass crops must never form
// an artificial union that could certify a blank region between HUD panels.
static_assert(!native_game_offscreen_color_regions_intersect(
    {0u, 0u, 80u, 80u}, {100u, 0u, 120u, 80u}));
static_assert(!native_game_offscreen_color_regions_intersect(
    {140u, 0u, 220u, 80u}, {100u, 0u, 120u, 80u}));

} // namespace outrun::vr::dx11
