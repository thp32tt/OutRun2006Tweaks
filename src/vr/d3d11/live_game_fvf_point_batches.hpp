#pragma once
// Preflight genuine game FVF D3DFILL_POINT clip-generated POINTLIST windows.
// Source triangles may expand to two or more post-clip fan triangles. The
// original D3D9 Draw stays authoritative on every failure; GPU upload and
// final pixel capture occur only after a complete bounded CPU source plan.
#include <cstddef>
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11::live_game_frame {
struct GameFvfNativePointBatchPlan {
    bool supported = false;
    std::uint32_t totalVertices = 0u;
    std::uint32_t verticesPerDraw = 0u;
    std::uint32_t draws = 0u;
};
[[nodiscard]] constexpr GameFvfNativePointBatchPlan
game_fvf_native_point_batch_plan(std::size_t total,
                                 std::uint32_t maxPerDraw,
                                 std::uint32_t maxExpanded) noexcept {
    GameFvfNativePointBatchPlan plan{};
    // Every clipped CPU polygon emits complete point-filled triangles.
    // A partial triangle, over-budget expansion or invalid Draw capacity
    // must never generate a partial frame or an incompletely clipped point.
    if (total == 0u || total % 3u != 0u ||
        total > maxExpanded ||
        total > (std::numeric_limits<std::uint32_t>::max)() ||
        maxPerDraw < 3u)
        return plan;
    // The actual clip fan budget can be far SMALLER than the 6144-vertex
    // GPU IA capacity (one source triangle has at most 42 point vertices).
    // It still uses one valid Draw; only total > maxExpanded is invalid.
    // Do not reject legitimate small menu/HUD and race geometry merely
    // because the device upload window has unused spare capacity.
    const std::uint32_t window = maxPerDraw - (maxPerDraw % 3u);
    if (window < 3u) return plan;
    plan.supported = true;
    plan.totalVertices = static_cast<std::uint32_t>(total);
    plan.verticesPerDraw = window;
    // Ceiling division without unsigned overflow; zero windows are invalid.
    plan.draws = 1u + (plan.totalVertices - 1u) / window;
    return plan;
}
// Six hardware and up to six D3D9 user planes plus the optional positive-W
// plane can add at most 13 vertices to one convex source triangle.
// Fan triangulation therefore requires no more than (3+13-2)*3 = 42
// authentic point occurrences per triangle. A 6144-element source STRIP
// may contain 6142 faces: derive a complete source-bounded CPU clip plan
// rather than rejecting real game geometry after arbitrary 4x growth.
[[nodiscard]] constexpr std::uint32_t game_fvf_native_point_expansion_budget(
    std::uint32_t topology, std::uint32_t sourceElements,
    std::uint32_t maxSourceElements) noexcept {
    if (sourceElements < 3u || sourceElements > maxSourceElements) return 0u;
    const std::uint32_t triangles =
        topology == 4u && sourceElements % 3u == 0u
            ? sourceElements / 3u
            : (topology == 5u || topology == 6u)
                ? sourceElements - 2u : 0u;
    constexpr std::uint32_t kMaxPointsPerSourceTriangle = 42u;
    if (!triangles ||
        triangles > (std::numeric_limits<std::uint32_t>::max)() /
                    kMaxPointsPerSourceTriangle)
        return 0u;
    return triangles * kMaxPointsPerSourceTriangle;
}

// Every triangle-aligned CPU-clipped point window uploads into the same
// dynamic D3D11 VB using a GPU-safe WRITE_DISCARD rename. Invalid plans do
// not mutate the caller's outputs or partially consume source geometry.
[[nodiscard]] constexpr bool game_fvf_native_point_batch_window(
    const GameFvfNativePointBatchPlan& plan, std::uint32_t ordinal,
    std::uint32_t& first, std::uint32_t& count) noexcept {
    if (!plan.supported || !plan.draws || ordinal >= plan.draws ||
        !plan.totalVertices || plan.totalVertices % 3u ||
        plan.verticesPerDraw < 3u || plan.verticesPerDraw % 3u)
        return false;
    const std::uint64_t begin =
        std::uint64_t(ordinal) * plan.verticesPerDraw;
    if (begin >= plan.totalVertices) return false;
    const std::uint32_t remaining =
        plan.totalVertices - static_cast<std::uint32_t>(begin);
    const std::uint32_t segment =
        remaining < plan.verticesPerDraw ? remaining : plan.verticesPerDraw;
    if (!segment || segment % 3u) return false;
    first = static_cast<std::uint32_t>(begin);
    count = segment;
    return true;
}
static_assert(game_fvf_native_point_expansion_budget(4u,6144u,6144u) == 86016u);
static_assert(game_fvf_native_point_expansion_budget(5u,6144u,6144u) == 257964u);
} // namespace outrun::vr::dx11::live_game_frame
