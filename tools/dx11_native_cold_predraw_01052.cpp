// 01052: real game pre-Draw backbuffer capture must not depend on a
// not-yet-created or stale native DX11 texture. Post-Draw still must.
#include "../src/vr/d3d11/native_game_pre_draw_surface.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using outrun::vr::dx11::live_game_frame::GameNativePreDrawSurface;
int main() {
    using S = GameNativePreDrawSurface;
    constexpr std::uint32_t argb=21u, xrgb=22u;
    static_assert(S::source_matches_canonical(3440,1440,argb,3440,1440,argb));
    static_assert(!S::source_matches_canonical(3440,1440,argb,1920,1080,argb));
    static_assert(!S::source_matches_canonical(3440,1440,argb,3440,1440,xrgb));
    static_assert(!S::source_matches_canonical(0,1440,argb,0,1440,argb));
    static_assert(!S::source_matches_canonical(65536,65536,argb,65536,65536,argb));
    // Cold boot: no native target exists, but the game's canonical D3D9
    // menu/backbuffer is valid and readable.
    static_assert(S::capture_extent_allowed(true,false,3440,1440,0,0));
    // Resolution Reset: the previous native dimensions are not authoritative.
    static_assert(S::capture_extent_allowed(true,false,3440,1440,1920,1080));
    // Real race postpass: DX11 CopySubresourceRegion must match its target.
    static_assert(!S::capture_extent_allowed(false,true,3440,1440,0,0));
    static_assert(!S::capture_extent_allowed(false,true,3440,1440,1920,1080));
    static_assert(S::capture_extent_allowed(false,true,3440,1440,3440,1440));
    static_assert(!S::capture_extent_allowed(false,false,3440,1440,3440,1440));
    static_assert(!S::capture_extent_allowed(true,true,65536,65536,0,0));
    S source{};
    constexpr std::uintptr_t device=0x1110u, backbuffer=0x2220u;
    const std::vector<std::uint8_t> pixels{1,2,3,255,4,5,6,255,
        7,8,9,255,10,11,12,255};
    assert(source.record(device,backbuffer,2,2,argb,pixels));
    // After native allocation, first SM3/FVF Draw performs strict source
    // identity and extent/format validation before using these real pixels.
    assert(source.matches(device,backbuffer,2,2,argb));
    assert(!source.matches(device,backbuffer,3,2,argb));
    assert(!source.matches(device+1,backbuffer,2,2,argb));
    assert(!source.matches(device,backbuffer,2,2,xrgb));
    assert(source.pixels==pixels);
    source.discard();
    assert(!source.active());
}
