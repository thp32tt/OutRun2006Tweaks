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
    TriangleList, TriangleStrip, TriangleFan,
    LineList, LineStrip, PointList
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
    // Actual D3D11 wireframe draws color clipped polygon edges rather than
    // the triangle interior. This guides real GPU PRE/POST sampling only.
    bool wireframe = false;
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
// A source-authentic SOLID FVF triangle whose three positive-W positions
// have exactly the same X/W or Y/W cannot rasterize an area. This proof
// uses products of the original float components promoted to double:
// binary32*binary32 fits exactly and is finite in binary64. Unlike an
// epsilon area test it never erases a thin but genuine road/HUD polygon.
// Source clip/RS/point/wireframe admission remains the caller's decision.
[[nodiscard]] inline bool native_raw_fvf_axis_collinear_positive_w(
    const std::array<std::array<double, 4u>, 3u>& source) noexcept {
    for (const auto& corner : source) {
        for (double value : corner)
            if (!std::isfinite(value)) return false;
        if (!(corner[3u] > 0.0)) return false;
    }
    const auto sameAxis = [&](unsigned axis) noexcept {
        for (unsigned corner = 1u; corner < 3u; ++corner)
            if (source[0u][axis] * source[corner][3u] !=
                source[corner][axis] * source[0u][3u])
                return false;
        return true;
    };
    return sameAxis(0u) || sameAxis(1u);
}
// A source-interior GPU capture center, derived from REAL post-clip triangle
// vertices. It is a sampling hint only: no CPU point grants pixel evidence.
struct NativeRawFvfInteriorSample {
    std::int64_t pixelX{}, pixelY{};
    // Another point strictly inside the SAME clipped authentic polygon.
    // May guide a second non-overlapping D3D11 GPU PRE/POST readback.
    std::int64_t alternatePixelX{}, alternatePixelY{};
    // Far-end pixel inside the same original clipped convex polygon.
    // Covers the opposite end of a skinny menu/race GPU triangle.
    std::int64_t oppositePixelX{}, oppositePixelY{};
    bool sparseDiagonal = false;
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
    // Enabled authentic FVF SV_ClipDistance0/1 source values, borrowed
    // strictly during the native GPU PRE/POST capture geometry calculation.
    std::size_t clipDistanceOffset = 0u;
    std::uint32_t clipDistanceMask = 0u;
};
// Clip each real assembled triangle against the SAME D3D11 clip volume
// (x,y in [-w,w], z in [0,w]) instead of bounding all raw IA vertices,
// including wholly offscreen/depth-clipped and degenerate geometry.
// Partial diagnostic output is still sampled from the actual GPU texture;
// no CPU polygon can substitute for the native pixel/RT/Present proof.
// Malformed homogeneous source (including the all-zero eye vector), IA,
// excessive geometry or unknown raster conditions revert to the existing
// full-viewport GPU source-sampling path. A finite nonzero W=0 eye-crossing
// triangle must be clipped before projection, exactly as the game FVF GPU
// POINTLIST source translation already does.
[[nodiscard]] inline bool native_raw_fvf_projected_raster(
    NativeRawFvfClipSpan source,
    float viewportX, float viewportY, float viewportW, float viewportH,
    NativeRawDrawExtent& raster,
    const NativeRawDrawExtent* sourceScissor = nullptr,
    const NativeRawFvfRaster* rasterState = nullptr,
    NativeRawFvfInteriorSample* interior = nullptr) noexcept {
    raster = {};
    if (interior) *interior = {};
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
                            source.indexCount > 1048576u)) ||
        // A line or point GPU IA is never a triangle fan for CPU sampling.
        // Its real GPU coverage is handled by the separate stroke path.
        (source.assembly != NativeRawFvfAssembly::TriangleList &&
         source.assembly != NativeRawFvfAssembly::TriangleStrip &&
         source.assembly != NativeRawFvfAssembly::TriangleFan) ||
        (source.clipDistanceMask & ~0x3fu) ||
        (source.clipDistanceMask &&
         (source.vertexStride < sizeof(float) * 6u ||
          source.clipDistanceOffset >
              source.vertexStride - sizeof(float) * 6u)))
        return false;
    const bool depthClipEnable = !rasterState || rasterState->depthClipEnable;
    const auto activeCount = source.indices ? source.indexCount : source.count;
    // No incomplete late original IA tail may make an earlier polygon look
    // like full source-authenticated RGB. Strip/fan share real endpoints.
    if (source.assembly == NativeRawFvfAssembly::TriangleList &&
        activeCount % 3u != 0u) return false;
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
    struct HomogeneousPoint {
        double x, y, z, w;
        std::array<double, 6u> userClip{};
    };
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
    double largestInteriorArea = 0.0;
    double interiorPixelX = 0.0, interiorPixelY = 0.0;
    double alternatePixelX = 0.0, alternatePixelY = 0.0;
    double oppositePixelX = 0.0, oppositePixelY = 0.0;
    bool interiorSparseDiagonal = false;
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
                // W=0 is an authentic perspective plane crossing when the
                // vector has finite nonzero XYZ. Reject the projectively
                // undefined zero vector, not the entire original game Draw.
                (!clip[0] && !clip[1] && !clip[2] && !clip[3]) ||
                (clip[3] > 0.0f && clip[3] <= 0.00001f)) return false;
            homogeneous[corner] = {static_cast<double>(clip[0]),
                                   static_cast<double>(clip[1]),
                                   static_cast<double>(clip[2]),
                                   static_cast<double>(clip[3])};
            if (source.clipDistanceMask) {
                float distances[6]{};
                std::memcpy(distances, bytes + vertex * source.vertexStride +
                            source.clipDistanceOffset, sizeof(distances));
                for (unsigned p = 0u; p < 6u; ++p) {
                    if (!(source.clipDistanceMask & (1u << p))) continue;
                    if (!std::isfinite(distances[p])) return false;
                    homogeneous[corner].userClip[p] = distances[p];
                }
            }
            // Only a valid W>0 input can be projected immediately. Source
            // W=0/W<0 requires homogeneous clipping, not division by zero.
            crossesEyePlane = crossesEyePlane || clip[3] <= 0.0f;
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
        // Draws. Only the all-zero homogeneous vector, nonfinite source
        // data and malformed IA fail closed; valid W=0 crosses this plane.
        if (crossesEyePlane || source.clipDistanceMask) {
            const auto distance = [](const HomogeneousPoint& q,
                                     unsigned plane) noexcept {
                switch (plane) {
                case 0u: return q.x + q.w;
                case 1u: return q.w - q.x;
                case 2u: return q.y + q.w;
                case 3u: return q.w - q.y;
                case 4u: return q.z;
                case 5u: return q.w - q.z;
                case 6u: return q.w - 0.00001;
                default: return q.userClip[plane - 7u];
                }
            };
            for (unsigned plane = 0u;
                 plane < (source.clipDistanceMask ? 13u : 7u) &&
                 polygonCount; ++plane) {
                if (plane >= 7u &&
                    !(source.clipDistanceMask & (1u << (plane - 7u))))
                    continue;
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
                        HomogeneousPoint intersection{
                            previous.x + t * (current.x - previous.x),
                            previous.y + t * (current.y - previous.y),
                            previous.z + t * (current.z - previous.z),
                            previous.w + t * (current.w - previous.w)};
                        for (unsigned c = 0u; c < 6u; ++c)
                            intersection.userClip[c] = previous.userClip[c] +
                                t * (current.userClip[c] - previous.userClip[c]);
                        clippedH[nextCount++] = intersection;
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
        // The old absolute 1e-12 area cutoff silently discarded genuine
        // one-ULP-wide menu/HUD/road triangles from the native GPU capture
        // population. Calculate oriented area around one clipped vertex:
        // shoelace subtraction at large screen positions cancels the tiny
        // remaining area even when the original source primitive is valid.
        // This remains a GPU PRE/POST sampling hint, never CPU pixel proof.
        const Point origin = polygon[0];
        double area = 0.0, areaMagnitude = 0.0;
        for (std::size_t i = 1u; i + 1u < polygonCount; ++i) {
            const double ax = polygon[i].x - origin.x;
            const double ay = polygon[i].y - origin.y;
            const double bx = polygon[i + 1u].x - origin.x;
            const double by = polygon[i + 1u].y - origin.y;
            const double crossA = ax * by, crossB = ay * bx;
            area += crossA - crossB;
            areaMagnitude += std::abs(crossA) + std::abs(crossB);
        }
        if (!std::isfinite(area) || !std::isfinite(areaMagnitude))
            return false;
        // Only an exact axis collapse can be confidently classified as a
        // zero-area solid source here. A diagonal collinearity or cancellation
        // may still be GPU-rasterized after subpixel quantization: retain its
        // extent instead of hiding a potentially changed real GPU pixel.
        bool sameX = true, sameY = true;
        for (std::size_t i = 1u; i < polygonCount; ++i) {
            sameX = sameX && polygon[i].x == origin.x;
            sameY = sameY && polygon[i].y == origin.y;
        }
        const bool lineOnly = area == 0.0 && (sameX || sameY);
        if (lineOnly && (!rasterState || !rasterState->wireframe ||
                         rasterState->cull != NativeRawFvfCull::None))
            continue;
        // Do not infer the opposite face from a cancellation-level area.
        // Missing a cull optimization is safe; omitting a live native RGB
        // capture from a thin source triangle is not.
        const bool reliableWinding = std::abs(area) >
            32.0 * (std::numeric_limits<double>::epsilon)() * areaMagnitude;
        if (!lineOnly && reliableWinding && rasterState &&
            rasterState->cull != NativeRawFvfCull::None) {
            // Viewport Y reverses the NDC polygon winding. A negative
            // NDC area is clockwise on the D3D11 screen render target;
            // FrontCounterClockwise reverses the accepted face.
            const bool sourceFront = rasterState->frontCounterClockwise
                ? area > 0.0 : area < 0.0;
            if ((sourceFront && rasterState->cull == NativeRawFvfCull::Front) ||
                (!sourceFront && rasterState->cull == NativeRawFvfCull::Back))
                continue;
        }
        // A screen-wide but very thin diagonal triangle can have a huge
        // bounding box whose 512x288 GPU sweep corners contain NO filled
        // pixels. The arithmetic mean of a clipped convex polygon's vertices
        // is strictly inside that genuine source polygon, including after
        // homogeneous W and the actual D3D11 scissor/face clipping.
        // Prefer an interior tile only for low-fill diagonal footprints;
        // broad triangles retain their existing rotating GPU source sweep.
        if (interior && (std::abs(area) > largestInteriorArea ||
                         (lineOnly && !anyVisible))) {
            double loX = (std::numeric_limits<double>::max)();
            double loY = loX;
            double hiX = -loX, hiY = -loX;
            double sumX = 0.0, sumY = 0.0;
            for (std::size_t i = 0u; i < polygonCount; ++i) {
                const auto& q = polygon[i];
                loX = (std::min)(loX, q.x);
                loY = (std::min)(loY, q.y);
                hiX = (std::max)(hiX, q.x);
                hiY = (std::max)(hiY, q.y);
                sumX += q.x;
                sumY += q.y;
            }
            const double boxArea = (hiX - loX) * (hiY - loY);
            const double centerX = sumX / static_cast<double>(polygonCount);
            const double centerY = sumY / static_cast<double>(polygonCount);
            double x = static_cast<double>(viewportX) +
                (centerX + 1.0) * static_cast<double>(viewportW) * 0.5;
            double y = static_cast<double>(viewportY) +
                (1.0 - centerY) * static_cast<double>(viewportH) * 0.5;
            if (!std::isfinite(boxArea) || !std::isfinite(x) ||
                !std::isfinite(y)) return false;
            // The original center-only RAW crop missed the distant half
            // of very long diagonal game triangles in the SAME Draw. Pick
            // the most distant clipped vertex in real viewport pixel units,
            // then stay strictly inside the convex clipped source polygon.
            // This is placement only: both captures must still prove real
            // D3D11 GPU RGB changes, source RT ownership and Present epoch.
            Point farthest = polygon[0];
            double farthestDistance = -1.0;
            for (std::size_t i = 0u; i < polygonCount; ++i) {
                const auto dx = (polygon[i].x - centerX) *
                    static_cast<double>(viewportW);
                const auto dy = (polygon[i].y - centerY) *
                    static_cast<double>(viewportH);
                const auto distance = dx * dx + dy * dy;
                if (!std::isfinite(distance)) return false;
                if (distance > farthestDistance) {
                    farthestDistance = distance;
                    farthest = polygon[i];
                }
            }
            // Two distinct endpoints of the real clipped polygon are
            // sampled inside its interior, rather than repeatedly copying
            // empty corners of a giant diagonal bounding rectangle.
            Point opposite = polygon[0];
            double longestSpan = -1.0;
            for (std::size_t i = 0u; i < polygonCount; ++i) {
                const double dx = (polygon[i].x - farthest.x) *
                    static_cast<double>(viewportW);
                const double dy = (polygon[i].y - farthest.y) *
                    static_cast<double>(viewportH);
                const double span = dx * dx + dy * dy;
                if (!std::isfinite(span)) return false;
                if (span > longestSpan) {
                    longestSpan = span;
                    opposite = polygon[i];
                }
            }
            const double nearOppositeX = centerX * 0.25 + opposite.x * 0.75;
            const double nearOppositeY = centerY * 0.25 + opposite.y * 0.75;
            double ox = static_cast<double>(viewportX) +
                (nearOppositeX + 1.0) * static_cast<double>(viewportW) * 0.5;
            double oy = static_cast<double>(viewportY) +
                (1.0 - nearOppositeY) * static_cast<double>(viewportH) * 0.5;
            if (!std::isfinite(ox) || !std::isfinite(oy)) return false;
            const double nearFarX = centerX * 0.25 + farthest.x * 0.75;
            const double nearFarY = centerY * 0.25 + farthest.y * 0.75;
            double ax = static_cast<double>(viewportX) +
                (nearFarX + 1.0) * static_cast<double>(viewportW) * 0.5;
            double ay = static_cast<double>(viewportY) +
                (1.0 - nearFarY) * static_cast<double>(viewportH) * 0.5;
            if (!std::isfinite(ax) || !std::isfinite(ay)) return false;
            if (rasterState && rasterState->wireframe) {
                // Native FVF wireframe emits pixels on the *post-clipped
                // edges*. A filled-polygon centroid can be far from every
                // drawn pixel, especially in a large game menu triangle.
                // Keep three authentic edge midpoints as the swept GPU
                // capture anchors; no CPU edge claims a pixel without the
                // original source/epoch and native PRE/POST RGB proof.
                std::array<Point,20u> edges{};
                std::size_t primary = 0u;
                double longest = -1.0;
                for (std::size_t e = 0u; e < polygonCount; ++e) {
                    const auto& a = polygon[e];
                    const auto& b = polygon[(e + 1u) % polygonCount];
                    const double dx = (b.x - a.x) * viewportW;
                    const double dy = (b.y - a.y) * viewportH;
                    const double length = dx * dx + dy * dy;
                    if (!std::isfinite(length)) return false;
                    edges[e] = {(a.x + b.x) * 0.5,
                                (a.y + b.y) * 0.5,
                                (a.z + b.z) * 0.5};
                    if (length > longest) { longest = length; primary = e; }
                }
                if (!(longest > 1.0e-12)) continue;
                // Widely separated native edge samples prevent both GPU
                // crops from repeatedly falling in the empty interior.
                std::size_t secondary = primary, tertiary = primary;
                double farthestEdge = -1.0, thirdSpread = -1.0;
                const auto pixelDistance2 = [&](std::size_t a,
                                                 std::size_t b) noexcept {
                    const double dx = (edges[a].x - edges[b].x) * viewportW;
                    const double dy = (edges[a].y - edges[b].y) * viewportH;
                    return dx * dx + dy * dy;
                };
                for (std::size_t e = 0u; e < polygonCount; ++e) {
                    if (e == primary) continue;
                    const double d = pixelDistance2(primary, e);
                    if (!std::isfinite(d)) return false;
                    if (d > farthestEdge) { farthestEdge = d; secondary = e; }
                }
                if (secondary == primary) return false;
                for (std::size_t e = 0u; e < polygonCount; ++e) {
                    if (e == primary || e == secondary) continue;
                    const double da = pixelDistance2(primary, e);
                    const double db = pixelDistance2(secondary, e);
                    if (!std::isfinite(da) || !std::isfinite(db)) return false;
                    const double spread = (std::min)(da, db);
                    if (spread > thirdSpread) { thirdSpread = spread; tertiary = e; }
                }
                if (tertiary == primary) return false;
                const auto screenX = [&](Point p) noexcept {
                    return static_cast<double>(viewportX) +
                        (p.x + 1.0) * static_cast<double>(viewportW) * 0.5;
                };
                const auto screenY = [&](Point p) noexcept {
                    return static_cast<double>(viewportY) +
                        (1.0 - p.y) * static_cast<double>(viewportH) * 0.5;
                };
                x = screenX(edges[primary]); y = screenY(edges[primary]);
                ax = screenX(edges[secondary]); ay = screenY(edges[secondary]);
                ox = screenX(edges[tertiary]); oy = screenY(edges[tertiary]);
                if (!std::isfinite(x) || !std::isfinite(y) ||
                    !std::isfinite(ax) || !std::isfinite(ay) ||
                    !std::isfinite(ox) || !std::isfinite(oy)) return false;
            }
            largestInteriorArea = std::abs(area);
            interiorPixelX = x;
            interiorPixelY = y;
            alternatePixelX = ax;
            alternatePixelY = ay;
            oppositePixelX = ox;
            oppositePixelY = oy;
            // Twice the polygon's area is stored in 'area'.
            interiorSparseDiagonal = (rasterState && rasterState->wireframe) ||
                (boxArea > 0.0 && std::abs(area) < boxArea * 0.25);
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
    if (interior) {
        if (!std::isfinite(interiorPixelX) || !std::isfinite(interiorPixelY) ||
            interiorPixelX < -maxCoordinate ||
            interiorPixelY < -maxCoordinate ||
            interiorPixelX >= maxCoordinate ||
            interiorPixelY >= maxCoordinate ||
            !std::isfinite(alternatePixelX) ||
            !std::isfinite(alternatePixelY) ||
            alternatePixelX < -maxCoordinate ||
            alternatePixelY < -maxCoordinate ||
            alternatePixelX >= maxCoordinate ||
            alternatePixelY >= maxCoordinate ||
            !std::isfinite(oppositePixelX) ||
            !std::isfinite(oppositePixelY) ||
            oppositePixelX < -maxCoordinate ||
            oppositePixelY < -maxCoordinate ||
            oppositePixelX >= maxCoordinate ||
            oppositePixelY >= maxCoordinate) return false;
        interior->pixelX = static_cast<std::int64_t>(std::floor(interiorPixelX));
        interior->pixelY = static_cast<std::int64_t>(std::floor(interiorPixelY));
        interior->alternatePixelX = static_cast<std::int64_t>(std::floor(alternatePixelX));
        interior->alternatePixelY = static_cast<std::int64_t>(std::floor(alternatePixelY));
        interior->oppositePixelX = static_cast<std::int64_t>(std::floor(oppositePixelX));
        interior->oppositePixelY = static_cast<std::int64_t>(std::floor(oppositePixelY));
        interior->sparseDiagonal = interiorSparseDiagonal;
    }
    return raster.right > raster.left && raster.bottom > raster.top;
}
} // namespace outrun::vr::dx11