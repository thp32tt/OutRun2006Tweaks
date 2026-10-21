#include "../src/vr/d3d11/live_game_volume_budget.hpp"
#include "../src/vr/d3d11/live_game_draw_mirror_cache.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    using namespace live_volume;
    static_assert(bounded_chain(4u,2u,2u,3u));
    static_assert(!bounded_chain(512u,512u,256u,10u));
    static_assert(!bounded_chain(0u,2u,2u,1u));
    static_assert(!bounded_chain(2u,2u,2u,5u));
    static_assert(matching_mip(8u,4u,2u,3u,1u,1u,1u));
    static_assert(!matching_mip(8u,4u,2u,1u,4u,2u,2u));
    using M=NativeSm3Texture2DMode;
    static_assert(native_sm3_volume_source_components(M::Implicit,0u)==7u);
    static_assert(native_sm3_volume_source_components(M::Gradients,2u)==7u);
    static_assert(native_sm3_volume_source_components(M::ExplicitLod,0u)==15u);
    static_assert(native_sm3_volume_source_components(M::Projected,0u)==0u);
    static_assert(!native_sm3_volume_modifier_supported(M::Projected,0u,0u));
    int id=1;
    const draw_mirror_cache::ViewKey volume{&id,false,true,false,true};
    const draw_mirror_cache::ViewKey cube{&id,false,true,true,false};
    assert(draw_mirror_cache::same_view(volume,volume));
    assert(!draw_mirror_cache::same_view(volume,cube));
    std::string hlsl;
    assert(append_native_sm3_texture3d_declarations(hlsl,1u));
    assert(hlsl.find("Texture3D<float4> r283_texture1")!=std::string::npos);
    assert(append_native_sm3_texture3d_sample(
        hlsl,"r0",15u,"r1",1u,4u,M::Gradients,"r2","r3"));
    assert(hlsl.find(".SampleGrad(")!=std::string::npos);
    assert(hlsl.find(").xyz, (r3).xyz")!=std::string::npos);
    assert(!append_native_sm3_texture3d_sample(
        hlsl,"r0",15u,"r1",1u,5u,M::Projected,"",""));
}
