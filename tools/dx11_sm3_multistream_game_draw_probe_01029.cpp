// Integration probe: D3D9 16 stream-source VB/IB/UP to native D3D11 SM3.
#include "../src/vr/d3d11/live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
static float channel(const std::vector<std::uint8_t>& b, unsigned v,
                     unsigned attribute, unsigned lane=0u) {
    const auto offset=std::size_t(v)*48u+attribute*16u+lane*4u;
    assert(offset+4u<=b.size());
    float x=0.f; std::memcpy(&x,b.data()+offset,4u); return x;
}
int main(){
    const float positions[2]{1.f,2.f}, materials[2]{5.f,9.f};
    const std::uint8_t colors[12]{11,22,33,255,40,50,60,128,70,80,90,64};
    std::array<GameSm3StreamView,16> streams{};
    streams[0]={reinterpret_cast<const std::uint8_t*>(positions),4u,2u};
    streams[4]={reinterpret_cast<const std::uint8_t*>(materials),4u,2u};
    streams[15]={colors,4u,3u};
    const std::vector<GameSm3ElementRef> elements{{0u,0u,0u},{4u,0u,0u},{15u,0u,4u}};
    std::vector<std::uint8_t> packed;
    assert(game_sm3_assemble_streams(elements,streams,2u,packed));
    assert(packed.size()==96u);
    assert(channel(packed,0,0)==1.f && channel(packed,1,0)==2.f);
    assert(channel(packed,0,1)==5.f && channel(packed,1,1)==9.f);
    assert(std::fabs(channel(packed,0,2)-33.f/255.f)<1.e-6f);
    assert(std::fabs(channel(packed,1,2,3)-128.f/255.f)<1.e-6f);
    std::array<std::uint32_t,16> step{};
    step[4]=2u; step[15]=1u;
    assert(game_sm3_assemble_instanced_streams(elements,streams,2u,3u,step,packed));
    assert(packed.size()==288u);
    assert(channel(packed,0,0)==1.f && channel(packed,5,0)==2.f);
    assert(channel(packed,0,1)==5.f && channel(packed,3,1)==5.f);
    assert(channel(packed,4,1)==9.f && channel(packed,5,1)==9.f);
    assert(std::fabs(channel(packed,4,2)-90.f/255.f)<1.e-6f);
    const auto correct=packed;
    auto stale=streams; stale[15].vertexCount=2u;
    assert(!game_sm3_assemble_instanced_streams(elements,stale,2u,3u,step,packed));
    stale=streams; stale[15].data=nullptr;
    assert(!game_sm3_assemble_instanced_streams(elements,stale,2u,3u,step,packed));
    assert(!game_sm3_assemble_streams({{16u,0u,0u}},streams,2u,packed));
    step[0]=1u;
    assert(!game_sm3_assemble_instanced_streams(elements,streams,2u,3u,step,packed));
    step[0]=0u;
    assert(!game_sm3_assemble_instanced_streams(
        elements,streams,1000000u,1000000u,step,packed));
    assert(packed==correct);
    return 0;
}
