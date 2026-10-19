#include "../src/vr/d3d11/live_game_sm3_stream_assembly.hpp"
#include "../src/vr/d3d11/live_game_sm3_sampler_slots.hpp"
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
static float value(const std::vector<std::uint8_t>& v, unsigned row,
                   unsigned attr, unsigned lane) {
    float out{}; std::memcpy(&out,v.data()+row*48u+attr*16u+lane*4u,4u);
    return out;
}
int main() {
    // D3D9 VS sampler namespace is distinct from pixel s0..s15.
    static_assert(game_sm3_sampler_source_slot(true,0u)==256u);
    static_assert(game_sm3_sampler_source_slot(true,3u)==259u);
    static_assert(game_sm3_sampler_source_slot(false,0u)==0u);
    static_assert(game_sm3_sampler_source_slot(false,15u)==15u);
    assert(game_sm3_sampler_source_slot(true,4u)==kGameSm3InvalidSamplerSlot);
    assert(game_sm3_sampler_source_slot(false,16u)==kGameSm3InvalidSamplerSlot);
    // Sparse index order [physical 8, physical 2] is equal in both VB shadows.
    const float p[6]{8.f,80.f,800.f,2.f,20.f,200.f};
    const std::uint8_t c[16]{
        1,2,3,255,0,0x3c,0,0x38,10,20,30,128,0,0x38,0,0x34};
    std::array<GameSm3StreamView,4> views{};
    views[0]={reinterpret_cast<const std::uint8_t*>(p),12u,2u};
    views[1]={c,8u,2u};
    std::vector<GameSm3ElementRef> e{
        {0u,0u,2u},{1u,0u,4u},{1u,4u,15u}};
    std::vector<std::uint8_t> out;
    assert(game_sm3_assemble_streams(e,views,2u,out));
    assert(out.size()==96u);
    assert(value(out,0,0,0)==8.f && value(out,1,0,0)==2.f);
    assert(value(out,0,0,3)==1.f);
    assert(std::fabs(value(out,0,1,0)-3.f/255.f)<1.e-6f);
    assert(std::fabs(value(out,1,1,3)-128.f/255.f)<1.e-6f);
    assert(value(out,0,2,0)==1.f && value(out,0,2,1)==0.5f);
    const auto saved=out;
    views[1].vertexCount=1u;
    assert(!game_sm3_assemble_streams(e,views,2u,out) && out==saved);
    views[1].vertexCount=2u; e[1].offset=7u;
    assert(!game_sm3_assemble_streams(e,views,2u,out) && out==saved);
    e[1].offset=0u; e[1].stream=4u;
    assert(!game_sm3_assemble_streams(e,views,2u,out) && out==saved);
    e[1].stream=1u; e[1].type=17u;
    assert(!game_sm3_assemble_streams(e,views,2u,out) && out==saved);
}
