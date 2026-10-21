#pragma once
#include "native_game_stretch_source.hpp"
#include <cstdint>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <array>
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
// A successful game-authored camera TARGET Clear writes real GPU pixels,
// including untouched menu/vehicle background areas. Its physical RTV
// subresource is still keyed separately; clear pixels are color source
// provenance for a later genuine GPU Copy/Stretch, not game Draw evidence.
// A partial Clear must certify only its actual clipped region.
[[nodiscard]] constexpr NativeGameOffscreenColorRegion
native_game_offscreen_clear_written_region(
    std::uint32_t width, std::uint32_t height, bool partial,
    std::int64_t left, std::int64_t top,
    std::int64_t right, std::int64_t bottom) noexcept {
    if (!width || !height) return {};
    if (!partial) return {0u, 0u, width, height};
    if (left < 0 || top < 0 || right <= left || bottom <= top ||
        right > static_cast<std::int64_t>(width) ||
        bottom > static_cast<std::int64_t>(height))
        return {};
    return {static_cast<std::uint32_t>(left),
            static_cast<std::uint32_t>(top),
            static_cast<std::uint32_t>(right),
            static_cast<std::uint32_t>(bottom)};
}
static_assert(native_game_offscreen_clear_written_region(
    100u, 80u, false, 0, 0, 0, 0).right == 100u);
static_assert(native_game_offscreen_clear_written_region(
    100u, 80u, true, 20, 10, 80, 70).left == 20u);
static_assert(!native_game_offscreen_color_region_valid(
    native_game_offscreen_clear_written_region(
        100u, 80u, true, -1, 0, 80, 70)));

// Merge only a rectangle union that is itself an exact rectangle. Camera
// menu panels frequently issue many side-by-side Draw/Clear writes; a
// 32-entry ring must preserve them without accepting holes between panels.
// Containment is valid; an L-shape, corner touch or separated slices are not.
[[nodiscard]] constexpr bool native_game_offscreen_exact_rect_union(
    NativeGameOffscreenColorRegion a,
    NativeGameOffscreenColorRegion b,
    NativeGameOffscreenColorRegion& joined) noexcept {
    joined = {};
    if (!native_game_offscreen_color_region_valid(a) ||
        !native_game_offscreen_color_region_valid(b)) return false;
    if (a.left <= b.left && a.top <= b.top &&
        a.right >= b.right && a.bottom >= b.bottom) {
        joined = a;
        return true;
    }
    if (b.left <= a.left && b.top <= a.top &&
        b.right >= a.right && b.bottom >= a.bottom) {
        joined = b;
        return true;
    }
    if (a.top == b.top && a.bottom == b.bottom &&
        a.left <= b.right && b.left <= a.right) {
        joined = {(std::min)(a.left, b.left), a.top,
                  (std::max)(a.right, b.right), a.bottom};
        return true;
    }
    if (a.left == b.left && a.right == b.right &&
        a.top <= b.bottom && b.top <= a.bottom) {
        joined = {a.left, (std::min)(a.top, b.top),
                  a.right, (std::max)(a.bottom, b.bottom)};
        return true;
    }
    return false;
}
[[nodiscard]] constexpr bool native_game_offscreen_color_regions_intersect(
    NativeGameOffscreenColorRegion draw,
    NativeGameOffscreenColorRegion copied) noexcept {
    return native_game_offscreen_color_region_valid(draw) &&
        native_game_offscreen_color_region_valid(copied) &&
        draw.left < copied.right && copied.left < draw.right &&
        draw.top < copied.bottom && copied.top < draw.bottom;
}


// A GPU StretchRect may display only part of the game camera when its
// destination straddles an eye edge. Replaying the real shader samples ONLY
// the visible destination pixel centers (with source crop clamping).
// Track those source texels, including both taps of a linear filter;
// unobserved clipped-out atlas texels must not reject a genuine camera
// postpass. At the same time, do not declare a missing sampled texel drawn.
[[nodiscard]] inline NativeGameOffscreenColorRegion
native_game_visible_stretch_sample_region(
    std::uint32_t sourceWidth, std::uint32_t sourceHeight,
    NativeGameOffscreenColorRegion source,
    std::uint32_t eyeWidth, std::uint32_t eyeHeight,
    std::int32_t destLeft, std::int32_t destTop,
    std::int32_t destRight, std::int32_t destBottom,
    bool linear) noexcept {
    if (!native_game_offscreen_color_region_valid(source)) return {};
    const auto visible = native_game_stretch_clipped_region(
        sourceWidth, sourceHeight, source.left, source.top,
        source.right, source.bottom, eyeWidth, eyeHeight,
        destLeft, destTop, destRight, destBottom);
    if (!visible.valid) return {};
    // Use double for the signed destination span (up to UINT32_MAX).
    // Hardware SampleLevel clamp is to the camera crop's edge texel centers.
    const auto sampleAxis = [linear](
        std::uint32_t srcStart, std::uint32_t srcEnd,
        std::uint32_t clippedStart, std::uint32_t clippedEnd,
        std::int32_t dstStart, std::int32_t dstEnd)
        noexcept -> std::array<std::uint32_t, 2u> {
        const double span = double(std::int64_t(dstEnd) - dstStart);
        if (span <= 0.0 || clippedStart >= clippedEnd)
            return {};
        const double srcSpan = double(srcEnd - srcStart);
        const double startCenter = double(srcStart) + 0.5;
        const double lastCenter = double(srcEnd) - 0.5;
        const auto sample = [&](double pixelCenter) noexcept {
            const double scaled = double(srcStart) +
                (pixelCenter - double(dstStart)) * srcSpan / span;
            return (std::max)(startCenter, (std::min)(lastCenter, scaled));
        };
        const double first = sample(double(clippedStart) + 0.5);
        const double last = sample(double(clippedEnd) - 0.5);
        const double tap = linear ? 0.5 : 0.0;
        // floor(u * sourceWidth) for point; bilinear also reads the
        // adjacent texel at u * sourceWidth +/- 0.5. One end is exclusive.
        const auto firstTexel = static_cast<std::uint32_t>(
            (std::max)(double(srcStart), std::floor(first - tap)));
        const auto lastTexel = static_cast<std::uint32_t>(
            (std::min)(double(srcEnd), std::floor(last + tap) + 1.0));
        return {firstTexel, lastTexel};
    };
    const auto x = sampleAxis(
        source.left, source.right, visible.left, visible.right,
        destLeft, destRight);
    const auto y = sampleAxis(
        source.top, source.bottom, visible.top, visible.bottom,
        destTop, destBottom);
    const NativeGameOffscreenColorRegion samples{x[0], y[0], x[1], y[1]};
    return native_game_offscreen_color_region_valid(samples) ? samples :
        NativeGameOffscreenColorRegion{};
}

 // Real game camera postpasses can copy more than the source's proven
 // color-written region. One intersecting Draw is NOT enough to certify
 // the complete native eye: require full 2D coverage by actual same-key
 // GPU Draw footprints, including disjoint adjacent viewport fragments.
 // Partition at every X edge so each slab has constant rectangle
 // membership, then prove Y has no gap. Bounded by the 32-entry ledger;
 // no allocation and no changes to the authoritative D3D9 game Draw.
 template <std::size_t N>
 [[nodiscard]] constexpr bool native_game_offscreen_color_region_fully_covered(
     NativeGameOffscreenColorRegion copied,
     const std::array<NativeGameOffscreenColorRegion, N>& written,
     std::size_t count) noexcept {
     if (!native_game_offscreen_color_region_valid(copied) || count > N)
         return false;
     auto x = copied.left;
     while (x < copied.right) {
         auto next = copied.right;
         for (std::size_t i = 0u; i < count; ++i) {
             const auto r = written[i];
             if (!native_game_offscreen_color_region_valid(r)) continue;
             if (r.left > x && r.left < next) next = r.left;
             if (r.right > x && r.right < next) next = r.right;
         }
         if (next <= x) return false;
         auto y = copied.top;
         while (y < copied.bottom) {
             auto furthest = y;
             for (std::size_t i = 0u; i < count; ++i) {
                 const auto r = written[i];
                 if (r.left <= x && r.right >= next &&
                     r.top <= y && r.bottom > furthest)
                     furthest = r.bottom;
             }
             if (furthest == y) return false;
             y = furthest;
         }
         x = next;
     }
     return true;
 }

// Require exact real GPU Draw/Clear footprints for each eye composite.
// The target pixels alone cannot authenticate a foreign mip/array eye or a
// source camera whose menu/car/race color was never written this frame.
template <std::size_t N>
[[nodiscard]] constexpr bool native_game_gpu_eye_composite_source_proven(
    NativeGameOffscreenColorKey sampledKey,
    NativeGameOffscreenColorRegion sampled,
    const std::array<NativeGameOffscreenColorKey, N>& keys,
    const std::array<NativeGameOffscreenColorRegion, N>& regions,
    std::size_t count) noexcept {
    if (!native_game_offscreen_color_region_valid(sampled) ||
        !sampledKey.resource || count > N) return false;
    std::array<NativeGameOffscreenColorRegion, N> matching{};
    std::size_t matchingCount = 0u;
    for (std::size_t i = 0u; i < count; ++i)
        if (native_game_offscreen_color_key_matches(sampledKey, keys[i]))
            matching[matchingCount++] = regions[i];
    return native_game_offscreen_color_region_fully_covered(
        sampled, matching, matchingCount);
}

// When many authentic game camera Draw/Clear tiles form a non-slicing
// mosaic, pairwise union alone cannot compact its 32-slot GPU pixel ledger.
// Consider only edge-connected tiles of the SAME physical mip and eye,
// and accept their bounding rectangle only with complete raster coverage.
template <std::size_t N>
[[nodiscard]] constexpr NativeGameOffscreenColorRegion
native_game_offscreen_color_mosaic_compaction(
    NativeGameOffscreenColorRegion incoming,
    const std::array<NativeGameOffscreenColorRegion, N>& sameKey,
    std::size_t count) noexcept {
    if (!native_game_offscreen_color_region_valid(incoming) || count > N)
        return incoming;
    auto envelope = incoming;
    bool expanded = true;
    while (expanded) {
        expanded = false;
        for (std::size_t i = 0u; i < count; ++i) {
            const auto r = sameKey[i];
            if (!native_game_offscreen_color_region_valid(r)) continue;
            const bool vertical =
                (r.bottom == envelope.top || r.top == envelope.bottom) &&
                r.left < envelope.right && envelope.left < r.right;
            const bool horizontal =
                (r.right == envelope.left || r.left == envelope.right) &&
                r.top < envelope.bottom && envelope.top < r.bottom;
            if (!native_game_offscreen_color_regions_intersect(r, envelope) &&
                !vertical && !horizontal) continue;
            const NativeGameOffscreenColorRegion next{
                (std::min)(r.left,envelope.left), (std::min)(r.top,envelope.top),
                (std::max)(r.right,envelope.right),
                (std::max)(r.bottom,envelope.bottom)};
            if (next.left != envelope.left || next.top != envelope.top ||
                next.right != envelope.right || next.bottom != envelope.bottom) {
                envelope = next;
                expanded = true;
            }
        }
    }
    if (envelope.left == incoming.left && envelope.top == incoming.top &&
        envelope.right == incoming.right && envelope.bottom == incoming.bottom)
        return incoming;
    std::array<NativeGameOffscreenColorRegion, N + 1u> proof{};
    proof[0] = incoming;
    for (std::size_t i = 0u; i < count; ++i) proof[i+1u] = sameKey[i];
    return native_game_offscreen_color_region_fully_covered(
        envelope, proof, count+1u) ? envelope : incoming;
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
