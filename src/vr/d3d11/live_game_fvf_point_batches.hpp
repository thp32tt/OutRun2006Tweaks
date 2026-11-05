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
        maxPerDraw < 3u || maxExpanded < maxPerDraw)
        return plan;
    const std::uint32_t window = maxPerDraw - (maxPerDraw % 3u);
    if (window < 3u) return plan;
    plan.supported = true;
    plan.totalVertices = static_cast<std::uint32_t>(total);
    plan.verticesPerDraw = window;
    plan.draws = static_cast<std::uint32_t>(
        (total + window - 1u) / window);
    return plan;
}
} // namespace outrun::vr::dx11::live_game_frame
