// 01055: a partial real D3D9 menu/vehicle/race postpass reads a
// cropped RT, while pre-Draw full seed and driver-failure fallback read
// the same original pixels at their authentic backbuffer coordinates.
#include "../src/vr/d3d11/native_game_surface_tile_plan.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceCopyRegion;
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceTilePlan;
int main() {
    using P = GameNativeSurfaceTilePlan;
    constexpr auto partial = GameNativeSurfaceCopyRegion::destination(
        2, 1, 4, 3, 6, 4);
    constexpr auto full = GameNativeSurfaceCopyRegion::destination(
        0, 0, 6, 4, 6, 4);
    static_assert(P::eligible(partial,6,4));
    static_assert(!P::eligible(full,6,4));
    static_assert(!P::eligible({},6,4));
    static_assert(!P::eligible(partial,3,4));
    static_assert(P::source_x(partial,true)==0u);
    static_assert(P::source_y(partial,true)==0u);
    static_assert(P::source_x(partial,false)==2u);
    static_assert(P::source_y(partial,false)==1u);
    // A tile RT stores precisely the original source region at origin 0.
    // Both paths must produce the SAME native D3D11 UpdateSubresource data.
    std::array<std::uint32_t,24> original{}, nativeFallback{}, nativeTile{};
    std::array<std::uint32_t,4> tile{};
    for(std::uint32_t y=0;y<4;++y)
        for(std::uint32_t x=0;x<6;++x)
            original[y*6+x]=0xff000000u | (y<<8u) | x;
    for(std::uint32_t y=0;y<2;++y)
        for(std::uint32_t x=0;x<2;++x)
            tile[y*2+x]=original[(y+1)*6+x+2];
    nativeFallback.fill(0x12345678u);
    nativeTile=nativeFallback;
    for(std::uint32_t y=0;y<2;++y)
        for(std::uint32_t x=0;x<2;++x) {
            const auto tx=partial.left+x, ty=partial.top+y;
            nativeFallback[ty*6+tx]=original[
                (P::source_y(partial,false)+y)*6 +
                 P::source_x(partial,false)+x];
            nativeTile[ty*6+tx]=tile[
                (P::source_y(partial,true)+y)*2 +
                 P::source_x(partial,true)+x];
        }
    assert(nativeTile==nativeFallback);
    assert(nativeTile[0]==0x12345678u); // other pixels unchanged
    assert(nativeTile[1*6+2]==original[1*6+2]);
}
