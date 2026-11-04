#pragma once
// Capture placement for REAL native FVF point and line Draws. This does not
// synthesize pixels, change the game Draw, or bypass native GPU PRE/POST proof.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include "native_game_raw_fvf_clip_capture.hpp"
#include "native_game_raw_dual_tile.hpp"

namespace outrun::vr::dx11 {
struct NativeRawStrokeEndpoints {
    std::int64_t ax{}, ay{}, bx{}, by{};
};

// Source clip-space IA is borrowed during this function only. Clip each
// actual D3D11 line/point against homogeneous XY/Z/W, enabled user planes,
// viewport and the already-owned native scissor. Point/line face culling does
// not apply. Invalid source data returns false and restores the established
// whole-viewport GPU capture; it never makes an unsafe Draw eligible.
[[nodiscard]] inline bool native_raw_fvf_stroke_dual_draw_tile(
    NativeRawFvfClipSpan source,
    float vx, float vy, float vw, float vh,
    std::uint32_t sw, std::uint32_t sh,
    std::uint32_t tw, std::uint32_t th,
    NativeRawDrawExtent admitted, std::uint32_t ordinal,
    NativeRawDrawExtent& raster, NativeRawDualTile& out,
    const NativeRawFvfRaster* rasterState = nullptr) noexcept {
    raster = {};
    out = {};
    const bool points = source.assembly == NativeRawFvfAssembly::PointList;
    const bool lines = source.assembly == NativeRawFvfAssembly::LineList ||
                       source.assembly == NativeRawFvfAssembly::LineStrip;
    const std::size_t active = source.indices ? source.indexCount : source.count;
    if ((!points && !lines) || !source.firstClip ||
        source.vertexStride < 4u * sizeof(float) ||
        source.vertexStride > 4096u || !source.count ||
        source.count > 1048576u || !active || active > 8192u ||
        (source.indices == nullptr) != (source.indexCount == 0u) ||
        source.count > (std::numeric_limits<std::size_t>::max)() /
            source.vertexStride ||
        (source.clipDistanceMask & ~0x3fu) ||
        (source.clipDistanceMask &&
         (source.vertexStride < 6u * sizeof(float) ||
          source.clipDistanceOffset >
              source.vertexStride - 6u * sizeof(float))) ||
        !std::isfinite(vx) || !std::isfinite(vy) ||
        !std::isfinite(vw) || !std::isfinite(vh) ||
        !(vw > 0.f) || !(vh > 0.f) ||
        !sw || !sh || !tw || !th || tw > sw || th > sh ||
        admitted.left >= admitted.right || admitted.top >= admitted.bottom ||
        (lines && active < 2u) ||
        // D3D9 LINELIST submits exactly two IA elements per source line.
        // A dangling indexed tail must not escape whole-source validation.
        (source.assembly == NativeRawFvfAssembly::LineList &&
         (active & 1u)))
        return false;
    const auto primitives = points ? active :
        source.assembly == NativeRawFvfAssembly::LineList
            ? active / 2u : active - 1u;
    if (!primitives) return false;
    const auto ndc = [](double v) noexcept {
        return (std::max)(-1.0, (std::min)(1.0, v));
    };
    const double left = ndc(2.0 * (admitted.left - double{vx}) / vw - 1.0);
    const double right = ndc(2.0 * (admitted.right - double{vx}) / vw - 1.0);
    const double bottom = ndc(1.0 - 2.0 * (admitted.bottom - double{vy}) / vh);
    const double top = ndc(1.0 - 2.0 * (admitted.top - double{vy}) / vh);
    if (!(right > left) || !(top > bottom)) return false;
    struct V {
        double x{}, y{}, z{}, w{};
        std::array<double, 6u> user{};
    };
    const auto* bytes = static_cast<const std::uint8_t*>(source.firstClip);
    const auto read = [&](std::size_t element, V& v) noexcept {
        const std::size_t index = source.indices ? source.indices[element] : element;
        if (index >= source.count) return false;
        float clip[4]{};
        std::memcpy(clip, bytes + index * source.vertexStride, sizeof(clip));
        for (float q : clip) if (!std::isfinite(q)) return false;
        // A real WVP line can cross the eye plane at W=0 (or W<0).
        // Clip its *homogeneous segment* before perspective division rather
        // than treating the endpoint as a malformed source. The eye and
        // XY/Z/user planes below admit only its genuinely visible portion.
        // A standalone point at W=0 cannot produce an authenticated pixel;
        // the all-zero homogeneous vector is invalid for either topology.
        if ((!clip[0] && !clip[1] && !clip[2] && !clip[3]) ||
            (points && clip[3] == 0.f))
            return false;
        v.x = clip[0]; v.y = clip[1]; v.z = clip[2]; v.w = clip[3];
        if (source.clipDistanceMask) {
            float user[6]{};
            std::memcpy(user, bytes + index * source.vertexStride +
                        source.clipDistanceOffset, sizeof(user));
            for (unsigned p = 0u; p < 6u; ++p) {
                if (!(source.clipDistanceMask & (1u << p))) continue;
                if (!std::isfinite(user[p])) return false;
                v.user[p] = user[p];
            }
        }
        return true;
    };
    const auto distance = [&](const V& v, unsigned plane) noexcept {
        switch (plane) {
        case 0u: return v.x + v.w;
        case 1u: return v.w - v.x;
        case 2u: return v.y + v.w;
        case 3u: return v.w - v.y;
        case 4u: return v.z;
        case 5u: return v.w - v.z;
        case 6u: return v.w - 0.00001;
        case 13u: return v.x - left * v.w;
        case 14u: return right * v.w - v.x;
        case 15u: return v.y - bottom * v.w;
        case 16u: return top * v.w - v.y;
        default: return v.user[plane - 7u];
        }
    };
    constexpr std::size_t kMaxPrimitives = 8192u;
    std::array<NativeRawStrokeEndpoints, kMaxPrimitives> visible{};
    std::size_t visibleCount = 0u;
    const auto limit = [](double p) noexcept {
        return std::isfinite(p) && p >= -4294967296.0 &&
               p < 4294967296.0;
    };
    NativeRawDrawExtent bounds{
        (std::numeric_limits<std::int64_t>::max)(),
        (std::numeric_limits<std::int64_t>::max)(),
        (std::numeric_limits<std::int64_t>::min)(),
        (std::numeric_limits<std::int64_t>::min)()};
    for (std::size_t i = 0u; i < primitives; ++i) {
        const std::size_t aIndex = points ? i :
            source.assembly == NativeRawFvfAssembly::LineList ? 2u * i : i;
        const std::size_t bIndex = points ? aIndex : aIndex + 1u;
        V a{}, b{};
        if (!read(aIndex, a) || !read(bIndex, b)) return false;
        double t0 = 0.0, t1 = 1.0;
        bool admittedPrimitive = true;
        for (unsigned p = 0u; p <= 16u; ++p) {
            if (p >= 7u && p <= 12u &&
                !(source.clipDistanceMask & (1u << (p - 7u))))
                continue;
            if (p == 4u || p == 5u) {
                if (rasterState && !rasterState->depthClipEnable) continue;
            }
            const double da = distance(a, p), db = distance(b, p);
            if (!std::isfinite(da) || !std::isfinite(db)) return false;
            if (da < 0.0 && db < 0.0) {
                admittedPrimitive = false; break;
            }
            if ((da < 0.0) != (db < 0.0)) {
                const double divisor = da - db;
                if (!std::isfinite(divisor) || divisor == 0.0) return false;
                const double t = da / divisor;
                if (!std::isfinite(t) || t < 0.0 || t > 1.0)
                    return false;
                if (da < 0.0) t0 = (std::max)(t0, t);
                else t1 = (std::min)(t1, t);
                if (t0 > t1) {
                    admittedPrimitive = false; break;
                }
            }
        }
        if (!admittedPrimitive) continue;
        const auto pixel = [&](double t, bool horizontal) noexcept {
            const double av = horizontal ? a.x : a.y;
            const double bv = horizontal ? b.x : b.y;
            const double w = a.w + t * (b.w - a.w);
            const double n = (av + t * (bv - av)) / w;
            return horizontal ? double{vx} + (n + 1.0) * double{vw} * 0.5 :
                double{vy} + (1.0 - n) * double{vh} * 0.5;
        };
        const double ax = pixel(t0, true), ay = pixel(t0, false);
        const double bx = pixel(t1, true), by = pixel(t1, false);
        if (!limit(ax) || !limit(ay) || !limit(bx) || !limit(by))
            return false;
        // The one-pixel D3D11 line/point raster and fractional viewport
        // quantization receive an outward 2px GPU sample margin.
        const auto l = static_cast<std::int64_t>(
            std::floor((std::min)(ax, bx) - 2.0));
        const auto t = static_cast<std::int64_t>(
            std::floor((std::min)(ay, by) - 2.0));
        const auto r = static_cast<std::int64_t>(
            std::ceil((std::max)(ax, bx) + 2.0));
        const auto bot = static_cast<std::int64_t>(
            std::ceil((std::max)(ay, by) + 2.0));
        const NativeRawDrawExtent clipped{
            (std::max)(l, admitted.left), (std::max)(t, admitted.top),
            (std::min)(r, admitted.right), (std::min)(bot, admitted.bottom)};
        if (clipped.right <= clipped.left ||
            clipped.bottom <= clipped.top) continue;
        bounds.left = (std::min)(bounds.left, clipped.left);
        bounds.top = (std::min)(bounds.top, clipped.top);
        bounds.right = (std::max)(bounds.right, clipped.right);
        bounds.bottom = (std::max)(bounds.bottom, clipped.bottom);
        visible[visibleCount++] = {
            static_cast<std::int64_t>(std::floor(ax)),
            static_cast<std::int64_t>(std::floor(ay)),
            static_cast<std::int64_t>(std::floor(bx)),
            static_cast<std::int64_t>(std::floor(by))};
    }
    if (!visibleCount) return false;
    raster = bounds;
    const auto tile = [&](std::int64_t x, std::int64_t y) noexcept {
        const auto clamp = [](std::int64_t v, std::uint32_t size,
                              std::uint32_t extent) noexcept {
            return static_cast<std::uint32_t>((std::max)(
                std::int64_t{0}, (std::min)(
                    v - static_cast<std::int64_t>(size) / 2,
                    static_cast<std::int64_t>(extent - size))));
        };
        return NativeRawTileOrigin{clamp(x, tw, sw), clamp(y, th, sh)};
    };
    const std::size_t chosen = static_cast<std::size_t>(ordinal) % visibleCount;
    const auto& a = visible[chosen];
    const std::uint32_t phase =
        static_cast<std::uint32_t>(ordinal / visibleCount) % 3u;
    // The single real source line can span the whole game's menu; move
    // along its endpoints on successive Draws instead of sampling its AABB
    // corners (which need not intersect any rendered line fragments).
    const auto blend = [&](std::uint32_t fraction) noexcept {
        return tile(a.ax + (a.bx - a.ax) * fraction / 4,
                    a.ay + (a.by - a.ay) * fraction / 4);
    };
    out.first = blend(phase == 0u ? 2u : phase == 1u ? 1u : 3u);
    const NativeRawTileOrigin otherEndpoints[2]{
        tile(a.ax, a.ay), tile(a.bx, a.by)};
    for (const auto& candidate : otherEndpoints) {
        if (!native_raw_source_tiles_disjoint(
                out.first, candidate, tw, th)) continue;
        out.second = candidate;
        out.hasSecond = true;
        return true;
    }
    for (std::size_t offset = 1u; offset < visibleCount; ++offset) {
        const auto& next = visible[(chosen + offset) % visibleCount];
        const auto candidate = tile(next.ax / 2 + next.bx / 2,
                                    next.ay / 2 + next.by / 2);
        if (!native_raw_source_tiles_disjoint(
                out.first, candidate, tw, th)) continue;
        out.second = candidate;
        out.hasSecond = true;
        return true;
    }
    NativeRawDualTile swept{};
    if (native_raw_swept_dual_draw_tile(
            sw, sh, tw, th, raster, ordinal, swept)) {
        if (native_raw_source_tiles_disjoint(
                out.first, swept.first, tw, th)) {
            out.second = swept.first;
            out.hasSecond = true;
        } else if (swept.hasSecond &&
                   native_raw_source_tiles_disjoint(
                       out.first, swept.second, tw, th)) {
            out.second = swept.second;
            out.hasSecond = true;
        }
    }
    return true;
}
} // namespace outrun::vr::dx11
