#pragma once
// Source-authored D3D9 SM3 polygon fill converted to native full-game GPU
// IA/RS drawing. Unknown states and oversized batches leave DX9Ex untouched.
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>
namespace outrun::vr::dx11::live_game_frame {
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
