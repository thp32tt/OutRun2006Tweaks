#pragma once
#include <array>
#include <cmath>
#include <cstdint>
namespace outrun::vr::dx11 {
// D3D9 fixed-function SetClipPlane is in WORLD coordinates, unlike SM3.
struct NativeGameFixedClipPlanes {
    std::uint32_t mask{};
    std::array<std::array<float, 4>, 6> world{};
};
[[nodiscard]] constexpr bool native_game_fixed_clip_mask_admitted(
    std::uint32_t mask, std::uint32_t maxPlanes, bool pretransformed) noexcept {
    if ((mask & ~0x3fu) != 0u || (mask && pretransformed)) return false;
    for (std::uint32_t i = 0u; i < 6u; ++i)
        if ((mask & (1u << i)) && i >= maxPlanes) return false;
    return true;
}
// Send signed per-vertex distances to GPU SV_ClipDistance to clip crossing
// primitives. Inactive user-plane slots must always be positive.
[[nodiscard]] inline bool native_game_fixed_clip_distances(
    const float* xyz, const float (&world)[4][4],
    const NativeGameFixedClipPlanes& planes,
    std::array<float, 8>& out) noexcept {
    out.fill(1.0f);
    if (!xyz) return false;
    if (!planes.mask) return true;
    if (!native_game_fixed_clip_mask_admitted(planes.mask,6u,false)) return false;
    const float p[4]{xyz[0],xyz[1],xyz[2],1.f};
    float transformed[4]{};
    for (unsigned c=0u;c<4u;++c) {
        for (unsigned k=0u;k<4u;++k)
            transformed[c] += p[k] * world[k][c];
        if (!std::isfinite(transformed[c])) return false;
    }
    for (unsigned i=0u;i<6u;++i) {
        if (!(planes.mask & (1u<<i))) continue;
        float distance=0.f;
        for (unsigned k=0u;k<4u;++k) {
            if (!std::isfinite(planes.world[i][k])) return false;
            distance += transformed[k] * planes.world[i][k];
        }
        if (!std::isfinite(distance)) return false;
        out[i]=distance;
    }
    return true;
}
} // namespace outrun::vr::dx11
