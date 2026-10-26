#pragma once
// Source-authored D3D9 SM3 polygon fill converted to native full-game GPU
// IA/RS drawing. Unknown states and oversized batches leave DX9Ex untouched.
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {

 // A bounded native fan window represents a contiguous set of authentic
 // source triangles, regardless of its D3D9 polygon fill mode. In point
 // mode the 3*N index occurrences are GPU POINTLIST vertices (including
 // shared center/seam duplicates), not a deduplicated vertex cloud.
 // Wire/solid mode interprets those same indices as native TRIANGLELIST.
 // Validate before any GPU upload so no malformed tail publishes a frame.
 struct GameSm3FanFillWindowPlan {
     bool supported = false;
     std::uint32_t nativeIndexCount = 0u;
     std::uint32_t sourceTriangles = 0u;
 };
 [[nodiscard]] constexpr GameSm3FanFillWindowPlan
 game_sm3_fan_fill_window_plan(
     std::uint32_t fill, std::uint32_t sourceElements,
     std::uint32_t firstRim, std::uint32_t windowElements,
     std::uint32_t maxNativeIndices) noexcept {
     if ((fill != 1u && fill != 2u && fill != 3u) ||
         sourceElements < 3u || firstRim == 0u ||
         firstRim >= sourceElements || windowElements < 3u ||
         windowElements - 1u > sourceElements - firstRim ||
         windowElements - 2u > maxNativeIndices / 3u)
         return {};
     const std::uint32_t triangles = windowElements - 2u;
     return {true, triangles * 3u, triangles};
 }
// A shader-bound real-game triangle strip may be split across dynamic GPU
// uploads in every D3D9 fill mode. Each chunk starts at an even source
// triangle ordinal; a POINTLIST must replay three occurrences per source
// triangle, while WIREFRAME/SOLID retain the true TRIANGLESTRIP raster.
struct GameSm3StripFillWindowPlan {
    bool supported = false;
    std::uint32_t sourceTriangles = 0u;
    std::uint32_t pointIndexCount = 0u;
};
[[nodiscard]] constexpr GameSm3StripFillWindowPlan
game_sm3_strip_fill_window_plan(
    std::uint32_t fill, std::uint32_t sourceElements,
    std::uint32_t firstElement, std::uint32_t windowElements,
    std::uint32_t maxPointIndices) noexcept {
    if ((fill != 1u && fill != 2u && fill != 3u) ||
        sourceElements < 3u || firstElement > sourceElements - 3u ||
        (firstElement & 1u) != 0u || windowElements < 3u ||
        windowElements > sourceElements - firstElement)
        return {};
    const auto triangles = windowElements - 2u;
    if (fill == 1u && triangles > maxPointIndices / 3u)
        return {};
    return {true, triangles, fill == 1u ? 3u * triangles : 0u};
}

// D3DRS_FILLMODE controls triangle polygons, not D3D9 POINTLIST/
// LINELIST/LINESTRIP. Those game Draws can inherit POINT/WIREFRAME from
// preceding triangles without changing their own primitive/raster semantics.
// Keep genuine shader-bound points and lines on native IA/VS/PS Draw paths.
struct GameSm3EffectivePolygonMode {
    bool admitted = false;
    bool pointTriangles = false;
    bool wireTriangles = false;
};
[[nodiscard]] constexpr GameSm3EffectivePolygonMode
game_sm3_effective_polygon_mode(
    std::uint32_t fill, std::uint32_t topology) noexcept {
    if (fill < 1u || fill > 3u || topology < 1u || topology > 6u)
        return {}; // Invalid source state remains D3D9-authoritative.
    const bool polygon = topology >= 4u;
    return {true, polygon && fill == 1u, polygon && fill == 2u};
}

[[nodiscard]] constexpr bool game_sm3_polygon_fill_admitted(
    std::uint32_t fill, std::uint32_t topology, std::uint32_t cull,
    bool lineAA, bool lastPixel, bool unitPoint) noexcept {
    if (fill == 3u) return true; // D3DFILL_SOLID
    if (topology < 4u || topology > 6u) return false;
    if (fill == 2u) return !lineAA && lastPixel; // D3DFILL_WIREFRAME
    if (fill == 1u) return cull == 1u && unitPoint; // D3DFILL_POINT
    return false;
}
[[nodiscard]] inline bool game_sm3_expand_polygon_points(
    std::uint32_t topology, const std::uint32_t* source,
    std::uint32_t count, std::uint32_t vertexCount,
    std::uint32_t maxIndices, std::vector<std::uint32_t>& output) noexcept {
    if (topology != 4u && topology != 5u && topology != 6u) return false;
    if (!vertexCount || count < 3u || !maxIndices ||
        (topology == 4u && count % 3u != 0u)) return false;
    const std::uint64_t triangles =
        topology == 4u ? count / 3u : std::uint64_t(count) - 2u;
    const std::uint64_t total = triangles * 3u;
    if (!triangles || total > maxIndices ||
        total > (1ull << 25u) / sizeof(std::uint32_t) ||
        total > (std::numeric_limits<std::uint32_t>::max)()) return false;
    for (std::uint32_t i = 0; i < count; ++i)
        if ((source ? source[i] : i) >= vertexCount) return false;
    try {
        std::vector<std::uint32_t> candidate(static_cast<std::size_t>(total));
        for (std::uint32_t tri = 0; tri < triangles; ++tri) {
            std::uint32_t a = 0u, b = 0u, c = 0u;
            if (topology == 4u) {
                a = tri * 3u; b = a + 1u; c = a + 2u;
            } else if (topology == 5u) {
                a = tri + (tri & 1u);
                b = tri + 1u - (tri & 1u);
                c = tri + 2u;
            } else {
                a = 0u; b = tri + 1u; c = tri + 2u;
            }
            const auto at = [&](std::uint32_t i) noexcept {
                return source ? source[i] : i;
            };
            const std::size_t dest = static_cast<std::size_t>(tri) * 3u;
            candidate[dest] = at(a);
            candidate[dest + 1u] = at(b);
            candidate[dest + 2u] = at(c);
        }
        output.swap(candidate);
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
