#pragma once
// Native game Draw sampler range for a REAL D3D9 managed source texture.
// BaseTexture::SetLOD and D3DSAMP_MAXMIPLEVEL independently discard finer
// levels; for an immutable D3D11 full-chain SRV, clamp both in the sampler.
// Never invent missing levels or silently downsample inaccessible source data.
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame::live_game_mip_lod {
// A managed D3D9 texture can select LOD N with MIPFILTER=NONE.
// Mirror real source levels through N; never synthesize or substitute a mip.
[[nodiscard]] constexpr std::uint32_t captured_levels(
    std::uint32_t sourceLevels, bool mipFiltering,
    std::uint32_t sourceLod) noexcept {
    if (!sourceLevels || sourceLod >= sourceLevels) return 0u;
    return mipFiltering ? sourceLevels : sourceLod + 1u;
}
struct Selection {
    bool valid{};
    std::uint32_t minLevel{};
    std::uint32_t maxLevel{};
};
[[nodiscard]] constexpr Selection select(std::uint32_t uploadedLevels,
    bool mipFiltering, std::uint32_t sourceLod,
    std::uint32_t maxMipLevel) noexcept {
    if (!uploadedLevels || sourceLod >= uploadedLevels ||
        (mipFiltering && maxMipLevel >= uploadedLevels) ||
        (!mipFiltering && maxMipLevel != 0u))
        return {};
    return {true, mipFiltering ?
        (sourceLod > maxMipLevel ? sourceLod : maxMipLevel) : sourceLod,
        mipFiltering ? uploadedLevels - 1u : sourceLod};
}
} // namespace outrun::vr::dx11::live_game_frame::live_game_mip_lod
