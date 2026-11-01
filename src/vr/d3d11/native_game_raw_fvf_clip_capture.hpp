#pragma once
// Source-authentic FVF native GPU PRE/POST capture geometry.
// This only guides bounded pixel sampling; source RT/Present identity,
// D3D11 GPU RGB delta, fences and original D3D9 fallback remain authoritative.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include "native_game_raw_draw_tile.hpp"
namespace outrun::vr::dx11 {
enum class NativeRawFvfAssembly : std::uint8_t {
    TriangleList, TriangleStrip, TriangleFan
};
struct NativeRawFvfClipSpan {
    const void* firstClip = nullptr;
    std::size_t vertexStride = 0u;
    std::size_t count = 0u;
    // Original D3D11 IA index stream. Unused VB vertices must never
    // influence genuine source-raster capture placement.
    const std::uint32_t* indices = nullptr;
    std::size_t indexCount = 0u;
    NativeRawFvfAssembly assembly = NativeRawFvfAssembly::TriangleList;
};
// Clip each real assembled triangle against the SAME D3D11 clip volume
// (x,y in [-w,w], z in [0,w]) instead of bounding all raw IA vertices,
// including wholly offscreen/depth-clipped and degenerate geometry.
// Partial diagnostic output is still sampled from the actual GPU texture;
// no CPU polygon can substitute for the native pixel/RT/Present proof.
// Unknown W, malformed IA, excessive geometry or unknown raster conditions
// revert to the existing full-viewport GPU source-sampling path.
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
            source.vertexStride ||
        (source.indices == nullptr) != (source.indexCount == 0u) ||
        (source.indices && (source.indexCount < 3u ||
                            source.indexCount > 1048576u)))
        return false;
    const auto activeCount = source.indices ? source.indexCount : source.count;
    const auto triangles = source.assembly == NativeRawFvfAssembly::TriangleList
        ? activeCount / 3u : activeCount - 2u;
    // Bounded diagnostic CPU geometry work; a very large genuine draw
    // always keeps the original viewport GPU-capture schedule.
    if (triangles == 0u || triangles > 8192u) return false;
    struct Point { double x, y, z; };
    const auto* bytes = static_cast<const std::uint8_t*>(source.firstClip);
    const auto plane_distance = [](Point p, int plane) noexcept {
        switch (plane) {
        case 0: return p.x + 1.0;
        case 1: return 1.0 - p.x;
        case 2: return p.y + 1.0;
        case 3: return 1.0 - p.y;
        case 4: return p.z;
        default: return 1.0 - p.z;
        }
    };
    double minX = (std::numeric_limits<double>::max)();
    double minY = minX;
    double maxX = -(std::numeric_limits<double>::max)();
    double maxY = maxX;
    bool anyVisible = false;
    for (std::size_t triangle = 0u; triangle < triangles; ++triangle) {
        std::array<Point, 12u> polygon{}, clipped{};
        for (std::size_t corner = 0u; corner < 3u; ++corner) {
            const auto element =
                source.assembly == NativeRawFvfAssembly::TriangleList
                    ? triangle * 3u + corner
                    : source.assembly == NativeRawFvfAssembly::TriangleStrip
                        ? triangle + corner
                        : corner == 0u ? 0u : triangle + corner;
            const auto vertex = source.indices
                ? static_cast<std::size_t>(source.indices[element]) : element;
            if (vertex >= source.count) return false;
            float clip[4]{};
            std::memcpy(clip, bytes + vertex * source.vertexStride, sizeof(clip));
            if (!std::isfinite(clip[0]) || !std::isfinite(clip[1]) ||
                !std::isfinite(clip[2]) || !std::isfinite(clip[3]) ||
                clip[3] <= 0.00001f) return false;
            const double invW = 1.0 / static_cast<double>(clip[3]);
            polygon[corner] = {static_cast<double>(clip[0]) * invW,
                               static_cast<double>(clip[1]) * invW,
                               static_cast<double>(clip[2]) * invW};
            if (!std::isfinite(polygon[corner].x) ||
                !std::isfinite(polygon[corner].y) ||
                !std::isfinite(polygon[corner].z)) return false;
        }
        std::size_t polygonCount = 3u;
        // Homogeneous triangle edges remain straight after perspective
        // division for positive W. NDC half-plane clipping preserves their
        // precise screen footprint without interpolating shader attributes.
        for (int plane = 0; plane < 6 && polygonCount; ++plane) {
            std::size_t nextCount = 0u;
            auto previous = polygon[polygonCount - 1u];
            auto previousDistance = plane_distance(previous, plane);
            for (std::size_t i = 0u; i < polygonCount; ++i) {
                const auto current = polygon[i];
                const auto distance = plane_distance(current, plane);
                const bool wasInside = previousDistance >= 0.0;
                const bool isInside = distance >= 0.0;
                if (wasInside != isInside) {
                    const double divisor = previousDistance - distance;
                    if (!std::isfinite(divisor) || divisor == 0.0 ||
                        nextCount >= clipped.size()) return false;
                    const double t = previousDistance / divisor;
                    clipped[nextCount++] = {
                        previous.x + t * (current.x - previous.x),
                        previous.y + t * (current.y - previous.y),
                        previous.z + t * (current.z - previous.z)};
                }
                if (isInside) {
                    if (nextCount >= clipped.size()) return false;
                    clipped[nextCount++] = current;
                }
                previous = current;
                previousDistance = distance;
            }
            polygonCount = nextCount;
            polygon = clipped;
        }
        if (polygonCount < 3u) continue;
        // A point or zero-area edge cannot color an RGB sample as a solid
        // triangle. It must not inflate a distant legitimate menu raster.
        double area = 0.0;
        for (std::size_t i = 0u; i < polygonCount; ++i) {
            const auto& a = polygon[i];
            const auto& b = polygon[(i + 1u) % polygonCount];
            area += a.x * b.y - b.x * a.y;
        }
        if (!std::isfinite(area)) return false;
        if (std::abs(area) <= 1.0e-12) continue;
        anyVisible = true;
        for (std::size_t i = 0u; i < polygonCount; ++i) {
            const auto& p = polygon[i];
            // A clipped plane intersection can land a few ULP beyond
            // +/-1 in floating point. Keep the 2px safety margin but
            // never let ceil/floor grow a source tile by a third pixel
            // outside the actual D3D11 clip volume on different CPUs.
            const double x = (std::min)(1.0, (std::max)(-1.0, p.x));
            const double y = (std::min)(1.0, (std::max)(-1.0, p.y));
            minX = (std::min)(minX, x);
            minY = (std::min)(minY, y);
            maxX = (std::max)(maxX, x);
            maxY = (std::max)(maxY, y);
        }
    }
    if (!anyVisible) return false; // retain viewport sampling for unknown pixels
    // Outward two-pixel rounding keeps both D3D9 and D3D11 edge pixels
    // eligible; caller independently intersects native viewport/scissor.
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
