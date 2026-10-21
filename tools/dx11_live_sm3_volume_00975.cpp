#include "../src/vr/d3d11/live_game_volume_budget.hpp"
#include "../src/vr/d3d11/live_game_volume_pixels.hpp"
#include "../src/vr/d3d11/live_game_mip_lod.hpp"
#include "../src/vr/d3d11/live_game_draw_mirror_cache.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    using namespace live_volume;
    using namespace live_game_mip_lod;
    // All live 2D/cube/volume shader Draw samplers must respect both the
    // game's managed source SetLOD and D3DSAMP_MAXMIPLEVEL.
    static_assert(select(6u, true, 2u, 0u).valid);
    static_assert(select(6u, true, 2u, 0u).minLevel == 2u);
    static_assert(select(6u, true, 1u, 3u).minLevel == 3u);
    static_assert(select(6u, true, 1u, 3u).maxLevel == 5u);
    static_assert(select(1u, false, 0u, 0u).valid);
    static_assert(!select(6u, true, 6u, 0u).valid);
    static_assert(!select(6u, true, 0u, 6u).valid);
    static_assert(!select(1u, false, 1u, 0u).valid);
    static_assert(!select(1u, false, 0u, 1u).valid);
    static_assert(!select(0u, true, 0u, 0u).valid);
    static_assert(bounded_chain_bytes(4u, 2u, 2u, 3u, 8u));
    static_assert(!bounded_chain_bytes(512u, 512u, 256u, 10u, 8u));
    static_assert(bytes_per_texel(PixelLayout::r16f) == 2u);
    static_assert(bytes_per_texel(PixelLayout::rgba16f) == 8u);
    static_assert(bytes_per_texel(PixelLayout::unsupported) == 0u);
    const std::uint8_t source[8]{1,2,3,4,5,6,7,8};
    std::uint8_t dest[8]{};
    assert(convert_row(source, dest, 2u, PixelLayout::bgra8));
    assert(dest[0] == 3u && dest[2] == 1u && dest[3] == 4u);
    assert(dest[4] == 7u && dest[6] == 5u && dest[7] == 8u);
    assert(convert_row(source, dest, 2u, PixelLayout::bgrx8));
    assert(dest[3] == 255u && dest[7] == 255u);
    assert(convert_row(source, dest, 2u, PixelLayout::rgba8));
    assert(dest[0] == 1u && dest[2] == 3u && dest[3] == 4u);
    assert(convert_row(source, dest, 2u, PixelLayout::rgbx8));
    assert(dest[3] == 255u && dest[7] == 255u);
    assert(convert_row(source, dest, 1u, PixelLayout::r16f));
    assert(dest[0] == 1u && dest[1] == 2u);
    assert(convert_row(source, dest, 1u, PixelLayout::rgba16f));
    assert(dest[0] == 1u && dest[7] == 8u);
    assert(!convert_row(source, dest, 2u, PixelLayout::unsupported));
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
