#pragma once
// Per-Draw native SM3 SRV sharing. D3D9 VS and PS have separate sampler
// state, but can sample an identical D3D9 2D image generation and mip chain.
namespace outrun::vr::dx11::live_game_frame::draw_mirror_cache {
struct ViewKey {
    const void* source = nullptr;
    bool srgb = false;
    bool mipChain = false;
};
[[nodiscard]] constexpr bool same_view(ViewKey a, ViewKey b) noexcept {
    return a.source != nullptr && b.source != nullptr &&
           a.source == b.source && a.srgb == b.srgb &&
           a.mipChain == b.mipChain;
}
} // namespace outrun::vr::dx11::live_game_frame::draw_mirror_cache
