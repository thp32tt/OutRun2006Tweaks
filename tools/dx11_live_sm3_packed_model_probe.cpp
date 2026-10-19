// Real shader-bound menu/car/race packed vertex -> native float4 conversion.
#include "../src/vr/d3d11/live_game_sm3_vertex_unpack.hpp"
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
using outrun::vr::dx11::live_game_frame::game_sm3_decl_width;
using outrun::vr::dx11::live_game_frame::game_sm3_unpack_attribute;

static std::array<std::uint8_t,4> encode(std::uint32_t x, std::uint32_t y,
                                          std::uint32_t z, std::uint32_t unused=3u) {
    const std::uint32_t raw=(x&1023u)|((y&1023u)<<10u)|((z&1023u)<<20u)|((unused&3u)<<30u);
    std::array<std::uint8_t,4> value{};
    std::memcpy(value.data(),&raw,sizeof(raw));
    return value;
}
int main() {
    static_assert(game_sm3_decl_width(13u)==4u && game_sm3_decl_width(14u)==4u);
    static_assert(game_sm3_decl_width(17u)==0u);
    std::array<float,4> out{};
    auto in=encode(0u,512u,1023u);
    assert(game_sm3_unpack_attribute(13u,in.data(),out));
    assert(out[0]==0.f && out[1]==512.f && out[2]==1023.f && out[3]==1.f);
    // Signed 10-bit -512 saturates to -1; +511 is +1; -1 stays -1/511.
    in=encode(512u,511u,1023u);
    assert(game_sm3_unpack_attribute(14u,in.data(),out));
    assert(out[0]==-1.f && out[1]==1.f && out[3]==1.f);
    assert(std::fabs(out[2]+1.f/511.f)<0.000001f);
    in=encode(512u,511u,1023u,0u);
    assert(game_sm3_unpack_attribute(14u,in.data(),out));
    assert(out[0]==-1.f && out[1]==1.f && out[3]==1.f);
    in=encode(513u,0u,511u);
    assert(game_sm3_unpack_attribute(14u,in.data(),out));
    assert(out[0]>-1.f && out[0]<0.f && out[1]==0.f && out[2]==1.f);
    const std::uint8_t bgra[]={255u,128u,0u,255u};
    assert(game_sm3_unpack_attribute(4u,bgra,out));
    assert(out[0]==0.f && out[2]==1.f && out[3]==1.f);
    const auto retained=out;
    assert(!game_sm3_unpack_attribute(17u,in.data(),out));
    assert(!game_sm3_unpack_attribute(14u,nullptr,out));
    assert(out==retained);
    return 0;
}
