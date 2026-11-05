#include "../src/vr/d3d11/live_game_mixed_bump_texture.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <limits>
namespace m=outrun::vr::dx11::live_game_frame::mixed_bump_texture;
static std::array<std::int16_t,4> decoded(std::array<std::uint8_t,4> src,
                                          m::Layout l,bool& ok){
    std::array<std::int16_t,4> out{};
    ok=m::unpack_row(src.data(),out.data(),1u,l);return out;
}
int main(){
    std::uint32_t pitch{};
    if(!m::source_row_bytes(1024u,m::Layout::x8l8v8u8,pitch)||pitch!=4096u||
       !m::output_row_bytes(1024u,pitch)||pitch!=8192u||
       m::output_row_bytes(0u,pitch)||
       m::output_row_bytes(std::numeric_limits<std::uint32_t>::max(),pitch)||
       m::sampleable(m::Layout::l6v5u5,true)||
       m::sampleable(m::Layout::unsupported,false))return 1;
    bool ok{};
    const auto l=decoded({0xf0u,0xfdu,0u,0u},m::Layout::l6v5u5,ok);
    if(!ok||l[0]!=-32768||l[1]!=32767||l[2]!=32767||l[3]!=32767)return 2;
    const auto x=decoded({0x80u,0x7fu,0x80u,0x23u},m::Layout::x8l8v8u8,ok);
    if(!ok||x[0]!=-32768||x[1]!=32767||x[2]<16300||x[2]>16600||x[3]!=32767)return 3;
    const auto c=decoded({0u,0u,0u,0u},m::Layout::cxv8u8,ok);
    if(!ok||c[2]!=32767||c[3]!=32767)return 4;
    const auto edge=decoded({127u,0u,0u,0u},m::Layout::cxv8u8,ok);
    if(!ok||edge[0]!=32767||edge[2]!=0)return 5;
    (void)decoded({127u,127u,0u,0u},m::Layout::cxv8u8,ok);
    if(ok)return 6;
    if(m::unpack_row(nullptr,&pitch,1u,m::Layout::l6v5u5)||
       m::unpack_row(&pitch,nullptr,1u,m::Layout::l6v5u5))return 7;
    const std::array<std::uint8_t,6> padded{0u,0u,64u,64u,0xaau,0xaau};
    std::array<std::uint8_t,18> output{};output.fill(0xccu);
    if(!m::unpack_row(padded.data(),output.data(),2u,m::Layout::cxv8u8)||
       output[16]!=0xccu||output[17]!=0xccu)return 8;
    std::puts("01070 PASS mixed bump game texture mips/stride/fallback");
}
