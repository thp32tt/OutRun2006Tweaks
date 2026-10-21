#pragma once
// Native game Draw sampler range for a REAL D3D9 managed source texture.
// BaseTexture::SetLOD and D3DSAMP_MAXMIPLEVEL independently discard finer
// levels; for an immutable D3D11 full-chain SRV, clamp both in the sampler.
// Never invent missing levels or silently downsample inaccessible source data.
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame::live_game_mip_lod {
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
        (!mipFiltering && (uploadedLevels != 1u ||
                           sourceLod != 0u || maxMipLevel != 0u)))
        return {};
    return {true, mipFiltering ?
        (sourceLod > maxMipLevel ? sourceLod : maxMipLevel) : 0u,
        mipFiltering ? uploadedLevels - 1u : 0u};
}
} // namespace outrun::vr::dx11::live_game_frame::live_game_mip_lod
