#pragma once
// Native full-frame FVF large-fan and point-filled strip windows.
// Lower original D3D9 triangle corners into bounded indexed D3D11
// TRIANGLELIST/POINTLIST submissions, preserving every shared corner and
// strip winding without changing the original D3D9 draw or game input.
#include <algorithm>
#include <cstdint>
#include <limits>
#include <vector>

namespace outrun::vr::dx11::live_game_frame {
struct GameFvfPolygonWindowPlan {
    std::uint32_t trianglesPerWindow = 0u;
    std::uint32_t windows = 0u;
};
[[nodiscard]] constexpr GameFvfPolygonWindowPlan
game_fvf_polygon_window_plan(std::uint32_t sourceTopology,
    std::uint32_t sourceElements, std::uint32_t maxNativeIndices,
    std::uint32_t maxWindows) noexcept {
    // D3DPT_TRIANGLESTRIP=5, TRIANGLEFAN=6. Both have N-2 triangles.
    if ((sourceTopology != 5u && sourceTopology != 6u) ||
        sourceElements < 3u || maxNativeIndices < 3u || !maxWindows)
        return {};
    const std::uint32_t capacity = maxNativeIndices / 3u;
    const std::uint64_t triangles = std::uint64_t(sourceElements) - 2u;
    const std::uint64_t windows = (triangles + capacity - 1u) / capacity;
    if (!windows || windows > maxWindows) return {};
    return {capacity, static_cast<std::uint32_t>(windows)};
}
[[nodiscard]] inline bool game_fvf_build_polygon_window(
    std::uint32_t sourceTopology, const std::uint32_t* sourceIndices,
    std::uint32_t sourceElements, std::uint32_t vertexCount,
    std::uint32_t firstTriangle, std::uint32_t triangleCount,
    std::uint32_t maxNativeIndices,
    std::vector<std::uint32_t>& destination) noexcept {
    if ((sourceTopology != 5u && sourceTopology != 6u) ||
        sourceElements < 3u || vertexCount == 0u || triangleCount == 0u ||
        firstTriangle >= sourceElements - 2u ||
        triangleCount > sourceElements - 2u - firstTriangle ||
        triangleCount > maxNativeIndices / 3u)
        return false;
    try {
        std::vector<std::uint32_t> fresh(std::size_t(triangleCount) * 3u);
        for (std::uint32_t n = 0u; n < triangleCount; ++n) {
            const auto t = firstTriangle + n;
            // Use global strip parity, not per-window parity; the first
            // triangle of an odd-offset window must not reverse winding.
            const std::uint32_t a = sourceTopology == 6u ? 0u : t + (t & 1u);
            const std::uint32_t b = sourceTopology == 6u ? t + 1u :
                                      t + 1u - (t & 1u);
            const std::uint32_t c = t + 2u;
            const auto at = [&](std::uint32_t i) noexcept {
                return sourceIndices ? sourceIndices[i] : i;
            };
            const std::uint32_t ia = at(a), ib = at(b), ic = at(c);
            if (ia >= vertexCount || ib >= vertexCount || ic >= vertexCount)
                return false;  // no partial destination mutation
            const auto dst = std::size_t(n) * 3u;
            fresh[dst] = ia;
            fresh[dst + 1u] = ib;
            fresh[dst + 2u] = ic;
        }
        destination.swap(fresh);
        return true;
    } catch (...) { return false; }
}
} // namespace outrun::vr::dx11::live_game_frame
