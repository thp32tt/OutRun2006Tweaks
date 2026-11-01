#pragma once
// Select a real native fixed-function triangle's source GPU capture region
// from the exact clip-space vertices sent to the D3D11 pass-through VS.
// Sampling guidance ONLY: never substitutes for the live GPU RGB delta,
// original game RT identity, Present visibility, fences or fallback.
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include "native_game_raw_draw_tile.hpp"
namespace outrun::vr::dx11 {
struct NativeRawFvfClipSpan {
    const void* firstClip = nullptr;
    std::size_t vertexStride = 0u;
    std::size_t count = 0u;
};
// All vertices must have a finite positive W. A crossing/unknown clip W,
// an unsupported primitive, or a suspicious viewport retains the original
// full-viewport sampling schedule rather than risking a missing native pixel.
[[nodiscard]] inline bool native_raw_fvf_projected_raster(
    NativeRawFvfClipSpan source,
    float viewportX, float viewportY, float viewportW, float viewportH,
    NativeRawDrawExtent& raster) noexcept {
    raster = {};
    if (!source.firstClip || source.vertexStride < sizeof(float) * 4u ||
        source.vertexStride > 4096u || source.count < 3u ||
        source.count > 1048576u ||
        !std::isfinite(viewportX) || !std::isfinite(viewportY) ||
        !std::isfinite(viewportW) || !std::isfinite(viewportH) ||
        viewportW <= 0.0f || viewportH <= 0.0f ||
        source.count > (std::numeric_limits<std::size_t>::max)() /
            source.vertexStride) return false;
    const auto* bytes = static_cast<const std::uint8_t*>(source.firstClip);
    double minX = (std::numeric_limits<double>::max)();
    double minY = minX;
    double maxX = -(std::numeric_limits<double>::max)();
    double maxY = maxX;
    for (std::size_t i = 0u; i < source.count; ++i) {
        float clip[4]{};
        std::memcpy(clip, bytes + i * source.vertexStride, sizeof(clip));
        if (!std::isfinite(clip[0]) || !std::isfinite(clip[1]) ||
            !std::isfinite(clip[2]) || !std::isfinite(clip[3]) ||
            clip[3] <= 0.00001f) return false;
        const double x = double{clip[0]} / clip[3];
        const double y = double{clip[1]} / clip[3];
        if (!std::isfinite(x) || !std::isfinite(y)) return false;
        minX = (std::min)(minX, x); maxX = (std::max)(maxX, x);
        minY = (std::min)(minY, y); maxY = (std::max)(maxY, y);
    }
    // 2px outward safety margin covers D3D9/D3D11 pixel-center rounding
    // and conservative triangle-edge rasterization. Source scissor/viewport
    // intersections and GPU RGB-delta proof are independently required.
    constexpr double margin = 2.0;
    const double l = double{viewportX} + (minX + 1.0) * double{viewportW} * 0.5 - margin;
    const double r = double{viewportX} + (maxX + 1.0) * double{viewportW} * 0.5 + margin;
    const double t = double{viewportY} + (1.0 - maxY) * double{viewportH} * 0.5 - margin;
    const double b = double{viewportY} + (1.0 - minY) * double{viewportH} * 0.5 + margin;
    constexpr double maxCoordinate = 4294967296.0;
    if (!std::isfinite(l) || !std::isfinite(r) ||
        !std::isfinite(t) || !std::isfinite(b) ||
        l < -maxCoordinate || t < -maxCoordinate ||
        r > maxCoordinate || b > maxCoordinate ||
        !(r > l) || !(b > t)) return false;
    raster = {static_cast<std::int64_t>(std::floor(l)),
              static_cast<std::int64_t>(std::floor(t)),
              static_cast<std::int64_t>(std::ceil(r)),
              static_cast<std::int64_t>(std::ceil(b))};
    return raster.right > raster.left && raster.bottom > raster.top;
}
} // namespace outrun::vr::dx11
