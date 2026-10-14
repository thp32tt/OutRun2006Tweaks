#pragma once
namespace outrun::vr::dx11::live_game_frame {
// Stage0/Stage1 can use distinct game-authored textures only with an exact
// shared UV transform and sampler. Other draw states fail closed to D3D9.
constexpr bool stage1_dual_texture_compatible(
    bool stage0, bool stage1, bool stage1Texture2D, bool sameUv,
    bool sameTransform, bool sameSampler) noexcept {
    return stage0 && stage1 && stage1Texture2D &&
           sameUv && sameTransform && sameSampler;
}
static_assert(stage1_dual_texture_compatible(true,true,true,true,true,true));
static_assert(!stage1_dual_texture_compatible(true,true,true,true,false,true));
} // namespace outrun::vr::dx11::live_game_frame
