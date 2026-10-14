#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
// Stage0/Stage1 may use distinct game-authored textures and native samplers,
// but only with the same proven UV/transform. Any unsupported stage-1 sampler
// state fails closed to the original D3D9 Draw/input.
constexpr bool stage1_dual_texture_compatible(
    bool stage0, bool stage1, bool stage1Texture2D, bool sameUv,
    bool sameTransform, bool nativeSamplerCompatible) noexcept {
    return stage0 && stage1 && stage1Texture2D &&
           sameUv && sameTransform && nativeSamplerCompatible;
}
// Match D3D9 sampler enums without requiring identical Stage0/Stage1 values.
// The caller still rejects ADDRESSW mismatches and exact sampler query failure.
constexpr bool stage1_game_sampler_supported(
    std::uint32_t u, std::uint32_t v, std::uint32_t minFilter,
    std::uint32_t magFilter, std::uint32_t mipFilter,
    std::uint32_t maxMipLevel, float mipBias,
    std::uint32_t maxAniso, std::uint32_t srgb) noexcept {
    const auto address = [](std::uint32_t a) constexpr noexcept {
        return a >= 1u && a <= 5u; // D3DTADDRESS_WRAP..MIRRORONCE
    };
    const bool aniso = minFilter == 3u &&
        (magFilter == 2u || magFilter == 3u) &&
        mipFilter == 2u && maxAniso >= 2u && maxAniso <= 16u;
    return address(u) && address(v) &&
        (((minFilter == 1u || minFilter == 2u) &&
          (magFilter == 1u || magFilter == 2u)) || aniso) &&
        mipFilter <= 2u && srgb <= 1u &&
        (mipFilter != 0u || (maxMipLevel == 0u && mipBias == 0.0f)) &&
        mipBias >= -16.0f && mipBias <= 15.99f;
}
static_assert(stage1_game_sampler_supported(1,3,2,1,2,1,-1.25f,1,0));
static_assert(stage1_game_sampler_supported(4,5,3,3,2,0,0.0f,16,1));
static_assert(!stage1_game_sampler_supported(9,3,2,1,2,0,0.0f,1,0));
static_assert(!stage1_game_sampler_supported(1,3,3,3,0,0,0.0f,16,0));
static_assert(!stage1_game_sampler_supported(1,3,2,1,0,1,0.0f,1,0));
static_assert(!stage1_game_sampler_supported(1,3,2,1,2,0,0.0f,1,2));
static_assert(stage1_dual_texture_compatible(true,true,true,true,true,true));
static_assert(!stage1_dual_texture_compatible(true,true,true,true,false,true));
} // namespace outrun::vr::dx11::live_game_frame
