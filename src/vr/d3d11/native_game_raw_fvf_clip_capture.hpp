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
// Bind source-authentic D3D11 RS face culling to the RAW GPU sampling
// geometry. This changes only the PRE/POST capture search; the real native
// Draw and the unmodified D3D9 gameplay/fallback remain authoritative.
enum class NativeRawFvfCull : std::uint8_t { None, Front, Back };
struct NativeRawFvfRaster {
    NativeRawFvfCull cull = NativeRawFvfCull::None;
    bool frontCounterClockwise = false;
    // TRUE for unbound/default D3D11 RS; FALSE omits only z clipping.
    // Hardware always clips x, y and strictly positive homogeneous W.
    bool depthClipEnable = true;
};
// Map the ACTUALLY bound D3D11 RS cull mode into the capture raster.
// A null RS object does not mean CULL_NONE: the D3D11 default state is
// SOLID, CULL_BACK and FrontCounterClockwise=FALSE. Sampling a culled
// menu/car triangle as if it colored the GPU loses the sparse real RGB
// islands. Invalid enum values cannot certify a source clip footprint;
// callers keep the original GPU viewport sampler in that case.
[[nodiscard]] constexpr bool native_raw_fvf_raster_from_d3d11(
    bool rasterStateBound, std::uint32_t cullMode,
    bool frontCounterClockwise, bool depthClipEnable,
    NativeRawFvfRaster& out) noexcept {
    out = {};
    if (!rasterStateBound) {
        out.cull = NativeRawFvfCull::Back;
        return true;
    }
    switch (cullMode) {
    case 1u: out.cull = NativeRawFvfCull::None; break; // D3D11_CULL_NONE
    case 2u: out.cull = NativeRawFvfCull::Front; break; // D3D11_CULL_FRONT
    case 3u: out.cull = NativeRawFvfCull::Back; break; // D3D11_CULL_BACK
    default: return false;
    }
    out.frontCounterClockwise = frontCounterClockwise;
    out.depthClipEnable = depthClipEnable;
    return true;
}
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
    NativeRawDrawExtent& raster,
    const NativeRawDrawExtent* sourceScissor = nullptr,
    const NativeRawFvfRaster* rasterState = nullptr) noexcept {
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
    const bool depthClipEnable = !rasterState || rasterState->depthClipEnable;
    const auto activeCount = source.indices ? source.indexCount : source.count;
    const auto triangles = source.assembly == NativeRawFvfAssembly::TriangleList
        ? activeCount / 3u : activeCount - 2u;
    // Bounded diagnostic CPU geometry work; a very large genuine draw
    // always keeps the original viewport GPU-capture schedule.
    if (triangles == 0u || triangles > 8192u) return false;
    // D3D11 scissor acts on the projected polygon, NOT on its bounding
    // rectangle: a diagonal primitive can have an overlapping AABB while
    // every actual pixel is outside the game's live scissor. Work in NDC
    // with the same source viewport and clip against all four edges.
    double scissorLeft = -1.0, scissorRight = 1.0;
    double scissorBottom = -1.0, scissorTop = 1.0;
    if (sourceScissor) {
        if (sourceScissor->left >= sourceScissor->right ||
            sourceScissor->top >= sourceScissor->bottom) return false;
        const double x0 = 2.0 * (static_cast<double>(sourceScissor->left) -
            static_cast<double>(viewportX)) / static_cast<double>(viewportW) - 1.0;
        const double x1 = 2.0 * (static_cast<double>(sourceScissor->right) -
            static_cast<double>(viewportX)) / static_cast<double>(viewportW) - 1.0;
        const double y0 = 1.0 - 2.0 * (static_cast<double>(sourceScissor->bottom) -
            static_cast<double>(viewportY)) / static_cast<double>(viewportH);
        const double y1 = 1.0 - 2.0 * (static_cast<double>(sourceScissor->top) -
            static_cast<double>(viewportY)) / static_cast<double>(viewportH);
        if (!std::isfinite(x0) || !std::isfinite(x1) ||
            !std::isfinite(y0) || !std::isfinite(y1)) return false;
        scissorLeft = (std::max)(-1.0, x0);
        scissorRight = (std::min)(1.0, x1);
        scissorBottom = (std::max)(-1.0, y0);
        scissorTop = (std::min)(1.0, y1);
        if (scissorLeft >= scissorRight ||
            scissorBottom >= scissorTop) return false;
    }
    struct Point { double x, y, z; };
    struct HomogeneousPoint { double x, y, z, w; };
    const auto* bytes = static_cast<const std::uint8_t*>(source.firstClip);
    const auto plane_distance = [&](Point p, int plane) noexcept {
        switch (plane) {
        case 0: return p.x + 1.0;
        case 1: return 1.0 - p.x;
        case 2: return p.y + 1.0;
        case 3: return 1.0 - p.y;
        case 4: return p.z;
        case 5: return 1.0 - p.z;
        case 6: return p.x - scissorLeft;
        case 7: return scissorRight - p.x;
        case 8: return p.y - scissorBottom;
        default: return scissorTop - p.y;
        }
    };
    double minX = (std::numeric_limits<double>::max)();
    double minY = minX;
    double maxX = -(std::numeric_limits<double>::max)();
    double maxY = maxX;
    bool anyVisible = false;
    for (std::size_t triangle = 0u; triangle < triangles; ++triangle) {
        std::array<Point, 20u> polygon{}, clipped{};
        std::array<HomogeneousPoint,20u> homogeneous{}, clippedH{};
        bool crossesEyePlane = false;
        for (std::size_t corner = 0u; corner < 3u; ++corner) {
            const auto element =
                source.assembly == NativeRawFvfAssembly::TriangleList
                    ? triangle * 3u + corner
                    : source.assembly == NativeRawFvfAssembly::TriangleStrip
                        // The D3D11 IA swaps the first two vertices on
                        // odd strips. Without this the cull-facing test
                        // misses every other real menu/race triangle.
                        ? triangle + ((triangle & 1u) && corner < 2u
                                          ? 1u - corner : corner)
                        : corner == 0u ? 0u : triangle + corner;
            const auto vertex = source.indices
                ? static_cast<std::size_t>(source.indices[element]) : element;
            if (vertex >= source.count) return false;
            float clip[4]{};
            std::memcpy(clip, bytes + vertex * source.vertexStride, sizeof(clip));
            if (!std::isfinite(clip[0]) || !std::isfinite(clip[1]) ||
                !std::isfinite(clip[2]) || !std::isfinite(clip[3]) ||
                clip[3] == 0.0f ||
                (clip[3] > 0.0f && clip[3] <= 0.00001f)) return false;
            homogeneous[corner] = {static_cast<double>(clip[0]),
                                   static_cast<double>(clip[1]),
                                   static_cast<double>(clip[2]),
                                   static_cast<double>(clip[3])};
            crossesEyePlane = crossesEyePlane || clip[3] < 0.0f;
            if (clip[3] > 0.0f) {
                const double invW = 1.0 / static_cast<double>(clip[3]);
                polygon[corner] = {static_cast<double>(clip[0]) * invW,
                                   static_cast<double>(clip[1]) * invW,
                                   static_cast<double>(clip[2]) * invW};
                if (!std::isfinite(polygon[corner].x) ||
                    !std::isfinite(polygon[corner].y) ||
                    !std::isfinite(polygon[corner].z)) return false;
            }
        }
        std::size_t polygonCount = 3u;
        // Real menu, vehicle and race triangles can straddle the eye plane:
        // clip their finite source homogeneous vertices BEFORE dividing W.
        // Keep the original positive-W NDC path unchanged for ordinary game
        // Draws. W=0, nonfinite source data and malformed IA still fail closed.
        if (crossesEyePlane) {
            const auto distance = [](const HomogeneousPoint& q,
                                     unsigned plane) noexcept {
                switch (plane) {
                case 0u: return q.x + q.w;
                case 1u: return q.w - q.x;
                case 2u: return q.y + q.w;
                case 3u: return q.w - q.y;
                case 4u: return q.z;
                case 5u: return q.w - q.z;
                default: return q.w - 0.00001;
                }
            };
            for (unsigned plane = 0u; plane < 7u && polygonCount; ++plane) {
                // D3D11 DepthClipEnable=FALSE drops only 0<=z<=w.
                // The eye-plane W and x/y bounds still apply to EVERY Draw.
                if (!depthClipEnable && (plane == 4u || plane == 5u))
                    continue;
                std::size_t nextCount = 0u;
                auto previous = homogeneous[polygonCount - 1u];
                auto prevDistance = distance(previous, plane);
                for (std::size_t i = 0u; i < polygonCount; ++i) {
                    const auto current = homogeneous[i];
                    const auto currentDistance = distance(current, plane);
                    const bool wasInside = prevDistance >= 0.0;
                    const bool isInside = currentDistance >= 0.0;
                    if (wasInside != isInside) {
                        const double divisor = prevDistance - currentDistance;
                        if (!std::isfinite(divisor) || divisor == 0.0 ||
                            nextCount >= clippedH.size()) return false;
                        const double t = prevDistance / divisor;
                        clippedH[nextCount++] = {
                            previous.x + t * (current.x - previous.x),
                            previous.y + t * (current.y - previous.y),
                            previous.z + t * (current.z - previous.z),
                            previous.w + t * (current.w - previous.w)};
                    }
                    if (isInside) {
                        if (nextCount >= clippedH.size()) return false;
                        clippedH[nextCount++] = current;
                    }
                    previous = current;
                    prevDistance = currentDistance;
                }
                polygonCount = nextCount;
                homogeneous = clippedH;
            }
            for (std::size_t i = 0u; i < polygonCount; ++i) {
                const auto& q = homogeneous[i];
                if (!std::isfinite(q.w) || !(q.w > 0.0)) return false;
                polygon[i] = {q.x / q.w, q.y / q.w, q.z / q.w};
                if (!std::isfinite(polygon[i].x) ||
                    !std::isfinite(polygon[i].y) ||
                    !std::isfinite(polygon[i].z)) return false;
            }
        }
        // Homogeneous triangle edges remain straight after perspective
        // division for positive W. NDC half-plane clipping preserves their
        // precise screen footprint without interpolating shader attributes.
        for (int plane = 0; plane < (sourceScissor ? 10 : 6) &&
             polygonCount; ++plane) {
            // Skip ONLY the D3D11 near/far depth planes when the bound
            // rasterizer disables depth clipping. Keep XY/scissor clipping,
            // raster face culling, W bounds and source IA validation.
            if (!depthClipEnable && (plane == 4 || plane == 5))
                continue;
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
        if (rasterState && rasterState->cull != NativeRawFvfCull::None) {
            // Viewport Y reverses the NDC polygon winding. A negative
            // NDC area is clockwise on the D3D11 screen render target;
            // FrontCounterClockwise reverses the accepted face.
            const bool sourceFront = rasterState->frontCounterClockwise
                ? area > 0.0 : area < 0.0;
            if ((sourceFront && rasterState->cull == NativeRawFvfCull::Front) ||
                (!sourceFront && rasterState->cull == NativeRawFvfCull::Back))
                continue;
        }
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
