#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame::live_volume {
[[nodiscard]] constexpr bool bounded_chain(std::uint32_t w, std::uint32_t h,
 std::uint32_t d, std::uint32_t levels) noexcept {
    if (!w || !h || !d || w > 512u || h > 512u || d > 256u ||
        !levels || levels > 10u) return false;
    auto largest = w > h ? w : h;
    if (d > largest) largest = d;
    std::uint32_t possible = 0;
    for (; largest; largest >>= 1u) ++possible;
    if (levels > possible) return false;
    constexpr std::uint64_t limit = 24ull << 20u;
    std::uint64_t used = 0u;
    for (std::uint32_t mip = 0u; mip < levels; ++mip) {
        const auto x = (w >> mip) ? (w >> mip) : 1u;
        const auto y = (h >> mip) ? (h >> mip) : 1u;
        const auto z = (d >> mip) ? (d >> mip) : 1u;
        const auto bytes = static_cast<std::uint64_t>(x) * y * z * 4u;
        if (bytes > limit - used) return false;
        used += bytes;
    }
    return true;
}
[[nodiscard]] constexpr bool matching_mip(std::uint32_t w, std::uint32_t h,
 std::uint32_t d, std::uint32_t mip, std::uint32_t x,
 std::uint32_t y, std::uint32_t z) noexcept {
    if (!w || !h || !d || mip >= 32u) return false;
    return x == ((w >> mip) ? (w >> mip) : 1u) &&
           y == ((h >> mip) ? (h >> mip) : 1u) &&
           z == ((d >> mip) ? (d >> mip) : 1u);
}
} // namespace outrun::vr::dx11::live_game_frame::live_volume
