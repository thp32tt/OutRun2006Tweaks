#pragma once
#include "live_game_mip_lod.hpp"
#include <cstdint>
// Per-Draw native SM3 SRV sharing. D3D9 VS and PS have separate sampler
// state, but can sample an identical D3D9 2D image generation and mip chain.
namespace outrun::vr::dx11::live_game_frame::draw_mirror_cache {
// The native SRV always contains every actual D3D9 level through SetLOD,
// including when MIPFILTER=NONE. The prior 1-level cache receipt rejected
// later VS/PS samplers using the same managed source with SetLOD > 0.
[[nodiscard]] constexpr std::uint32_t mirrored_source_levels(
    std::uint32_t sourceLevels, bool mipChain, std::uint32_t sourceLod) noexcept {
    return live_game_mip_lod::captured_levels(sourceLevels, mipChain, sourceLod);
}
[[nodiscard]] constexpr bool cached_sampler_compatible(
    std::uint32_t cachedLevels, std::uint32_t sourceLevels,
    bool mipChain, std::uint32_t sourceLod, std::uint32_t maxMipLevel) noexcept {
    const auto expected = mirrored_source_levels(sourceLevels, mipChain, sourceLod);
    return expected != 0u && cachedLevels == expected &&
        live_game_mip_lod::select(cachedLevels, mipChain, sourceLod, maxMipLevel).valid;
}
struct ViewKey {
    const void* source = nullptr;
    bool srgb = false;
    bool mipChain = false;
    // Keep reflected six-face images distinct from 2D shader views.
    bool cube = false;
    bool volume = false;
};
[[nodiscard]] constexpr bool same_view(ViewKey a, ViewKey b) noexcept {
    return a.source != nullptr && b.source != nullptr &&
           a.source == b.source && a.srgb == b.srgb &&
           a.mipChain == b.mipChain && a.cube == b.cube && a.volume == b.volume;
}
} // namespace outrun::vr::dx11::live_game_frame::draw_mirror_cache
