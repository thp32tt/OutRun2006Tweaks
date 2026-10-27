#pragma once
namespace outrun::vr::dx11::live_game_frame {
// Admit a complete authentic D3D9 surface-copy color seed before the first
// SM3/FVF game Draw. This predicate alone creates no GPU output: a successful
// full-size readback must be stored and replayed first. Fail closed for
// partial/foreign/prior-draw/unreplayed color, preserving DX9Ex and input.
[[nodiscard]] constexpr bool native_game_full_surface_copy_can_seed(
    bool wholeSurface, bool noExistingSeed,
    bool noSourceDraws, bool pristineNativeEpoch,
    bool canonicalGameOwner, bool boundMainBackbuffer,
    bool noUnreplayedWrites) noexcept {
    return wholeSurface && noExistingSeed && noSourceDraws &&
        pristineNativeEpoch && canonicalGameOwner && boundMainBackbuffer &&
        noUnreplayedWrites;
}
} // namespace outrun::vr::dx11::live_game_frame
