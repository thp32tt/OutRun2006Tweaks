#include "../src/vr/d3d11/live_game_a8p8_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::a8p8_texture;
static_assert(source_bytes_per_texel() == 2u);
int main() {
    std::array<Rgb,256> palette{};
    palette[2] = {200, 31, 4};
    palette[7] = {6, 140, 250};
    palette[255] = {255, 0, 99};
    // Two 2-pixel rows with explicit padding between source rows.
    constexpr std::array<std::uint8_t,12> source{
        2,255, 7,0, 0xee,0xee,
        255,128, 2,17, 0xdd,0xdd};
    std::array<std::uint8_t,20> out{};
    out.fill(19);
    for(unsigned row=0;row<2u;++row)
        unpack_row(source.data()+row*6u,out.data()+row*8u,2u,palette.data());
    assert((out == std::array<std::uint8_t,20>{
        4,31,200,255, 250,140,6,0,
        99,0,255,128, 4,31,200,17, 19,19,19,19}));
    // 1x1 last mip preserves explicit alpha, even when palette index is 255.
    constexpr std::array<std::uint8_t,4> mip{255,51,0xab,0xcd};
    out.fill(19);
    unpack_row(mip.data(),out.data(),1u,palette.data());
    assert((std::array<std::uint8_t,4>{out[0],out[1],out[2],out[3]} ==
            std::array<std::uint8_t,4>{99,0,255,51}));
    for(unsigned i=4;i<out.size();++i)assert(out[i]==19u);
    unpack_row(mip.data(),out.data(),0u,palette.data());
    assert(out[0]==99u && out[3]==51u);
}
