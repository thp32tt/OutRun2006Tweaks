#include "../src/vr/d3d11/live_game_rg16_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::rg16_texture;
static_assert(expand16(0u) == 0u && expand16(32768u) == 128u && expand16(65535u) == 255u);
int main() {
    constexpr std::array<std::uint8_t, 20> source{
        0xff,0xff,0x00,0x00, 0x00,0x00,0xff,0xff, 0xaa,0xbb,
        0x00,0x80,0xff,0x7f, 0x01,0x00,0xff,0xff, 0xcc,0xdd};
    std::array<std::uint8_t,20> out{};
    out.fill(19u);
    for(unsigned y=0; y<2u; ++y)
        unpack_row(source.data()+y*10u,out.data()+y*8u,2u);
    assert((out == std::array<std::uint8_t,20>{
        0,0,255,255, 0,255,0,255,
        0,127,128,255, 0,255,0,255, 19,19,19,19}));
    constexpr std::array<std::uint8_t,8> mip{0xff,0x7f,0x00,0x80,0xee,0xdd,0xcc,0xbb};
    out.fill(19u);
    unpack_row(mip.data(),out.data(),1u);
    assert((std::array<std::uint8_t,4>{out[0],out[1],out[2],out[3]} ==
            std::array<std::uint8_t,4>{0,128,127,255}));
    for(unsigned i=4u;i<out.size();++i)assert(out[i]==19u);
    unpack_row(mip.data(),out.data(),0u);
    assert(out[0]==0u&&out[3]==255u);
}
