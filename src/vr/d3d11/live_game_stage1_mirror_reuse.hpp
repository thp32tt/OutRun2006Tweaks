#pragma once
// Native game Stage1 texture reuse decision, independent of Windows SDK.
// A shared D3D9 resource can use the already uploaded D3D11 pixels even with
// different addressing, filters or FVF UV, provided view encoding and mip
// completeness agree. Otherwise the original dedicated mirror is required.
namespace outrun::vr::dx11::live_game_frame {
constexpr bool stage1_game_mirror_reusable(bool sameSourceTexture,
                                           bool sameSrgbEncoding,
                                           bool stage0UsesMips,
                                           bool stage1UsesMips,
                                           bool stage0NativeViewReady) noexcept {
    return sameSourceTexture && sameSrgbEncoding &&
           stage0UsesMips == stage1UsesMips && stage0NativeViewReady;
}
static_assert(stage1_game_mirror_reusable(true,true,true,true,true));
static_assert(stage1_game_mirror_reusable(true,true,false,false,true));
static_assert(!stage1_game_mirror_reusable(false,true,true,true,true));
static_assert(!stage1_game_mirror_reusable(true,false,true,true,true));
static_assert(!stage1_game_mirror_reusable(true,true,false,true,true));
static_assert(!stage1_game_mirror_reusable(true,true,true,true,false));
} // namespace outrun::vr::dx11::live_game_frame
