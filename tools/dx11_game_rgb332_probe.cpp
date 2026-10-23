#include "../src/vr/d3d11/live_game_rgb332_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::rgb332_texture;
static_assert(source_bytes_per_texel(Layout::rgb332) == 1u);
static_assert(source_bytes_per_texel(Layout::a8rgb332) == 2u);
static_assert(expand3(0u) == 0u && expand3(7u) == 255u);
static_assert(expand2(0u) == 0u && expand2(3u) == 255u);
int main() {
    // Two padded game LockRect rows become adjacent tightly packed BGRA8 rows.
    constexpr std::array<std::uint8_t,8> source{0xe3,0x1c,0xaa,0xaa,
                                                 0x00,0xff,0xbb,0xbb};
    std::array<std::uint8_t,20> pixels{};
    pixels.fill(17u);
    for (unsigned row=0;row<2u;++row)
        unpack_row(source.data()+row*4u,pixels.data()+row*8u,2u,Layout::rgb332);
    assert((pixels == std::array<std::uint8_t,20>{
        255,0,255,255, 0,255,0,255,
        0,0,0,255, 255,255,255,255, 17,17,17,17}));
    // A8R3G3B2 carries per-texel alpha instead of relying on a palette.
    constexpr std::array<std::uint8_t,12> sourceAlpha{
        0xe3,0, 0x1c,127, 0xaa,0xaa,
        0x00,51, 0xff,255, 0xbb,0xbb};
    pixels.fill(17u);
    for (unsigned row=0;row<2u;++row)
        unpack_row(sourceAlpha.data()+row*6u,pixels.data()+row*8u,2u,Layout::a8rgb332);
    assert((pixels == std::array<std::uint8_t,20>{
        255,0,255,0, 0,255,0,127,
        0,0,0,51, 255,255,255,255, 17,17,17,17}));
    // One-pixel final mip must not read beyond a two-byte source texel.
    constexpr std::array<std::uint8_t,4> mip{0xa5,29,0xaa,0xbb};
    pixels.fill(17u);
    unpack_row(mip.data(),pixels.data(),1u,Layout::a8rgb332);
    assert((std::array<std::uint8_t,4>{pixels[0],pixels[1],pixels[2],pixels[3]} ==
            std::array<std::uint8_t,4>{85,36,182,29}));
    for(unsigned i=4;i<pixels.size();++i) assert(pixels[i]==17u);
    unpack_row(mip.data(),pixels.data(),0u,Layout::a8rgb332);
    assert(pixels[3]==29u);
}
