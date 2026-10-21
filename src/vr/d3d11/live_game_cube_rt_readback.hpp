#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame::cube_rt_readback {
// Bound all six GPU-authored BGRA8 faces including sampled mip levels.
// 24 MiB is one complete cube budget, never a per-face limit.
[[nodiscard]] constexpr bool bounded_six_face_bgra8(
    std::uint32_t edge, std::uint32_t levels) noexcept {
    if (!edge || edge > 1024u || !levels || levels > 11u) return false;
    std::uint32_t possible = 0u;
    for (auto n = edge; n; n >>= 1u) ++possible;
    if (levels > possible) return false;
    constexpr std::uint64_t maximum = 24ull << 20u;
    std::uint64_t total = 0u;
    for (std::uint32_t mip = 0u; mip < levels; ++mip) {
        const std::uint64_t side = (edge >> mip) ? (edge >> mip) : 1u;
        const std::uint64_t face = side * side * 4u;
        if (face > (maximum - total) / 6u) return false;
        total += face * 6u;
    }
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame::cube_rt_readback
