// Real ps_3_0 game samplers can swizzle sampled texels before write masking.
// This is integrated with native_backend's sN operand and HLSL emitters.
#include "native_sm3_texture_codegen.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    static_assert(native_sm3_sampler_swizzle_valid(0x00u));
    static_assert(native_sm3_sampler_swizzle_valid(0xffu));
    static_assert(!native_sm3_sampler_swizzle_valid(0x100u));
    std::string out;
    assert(append_native_sm3_texture2d_sample(out,"r283_t1",0x5u,
        "r283_t0",2u,14u,NativeSm3Texture2DMode::Projected,
        {},{},0x1bu));
    assert(out.find(".Sample(r283_sampler2, ((r283_t0).xy / (r283_t0).w)") !=
        std::string::npos);
    assert(out.find("r283_t1.xz = r283_texel_14.wy;") != std::string::npos);
    out.clear();
    assert(append_native_sm3_texture2d_sample(out,"r283_t1",0xau,
        "r283_t0",2u,15u,NativeSm3Texture2DMode::Bias,
        {},{},0x1bu));
    assert(out.find(".SampleBias(") != std::string::npos);
    assert(out.find("r283_t1.yw = r283_texel_15.zx;") != std::string::npos);
    out.clear();
    assert(append_native_sm3_texture2d_sample(out,"r283_t1",0xfu,
        "r283_t0",2u,16u,NativeSm3Texture2DMode::Gradients,
        "r283_dx","r283_dy",0x00u));
    assert(out.find(".SampleGrad(") != std::string::npos);
    assert(out.find("r283_t1.xyzw = r283_texel_16.xxxx;") != std::string::npos);
    out.clear();
    assert(append_native_sm3_texture2d_sample(out,"r283_t1",0x3u,
        "r283_t0",2u,17u,NativeSm3Texture2DMode::ExplicitLod));
    assert(out.find(".SampleLevel(") != std::string::npos);
    assert(out.find("r283_t1.xy = r283_texel_17.xy;") != std::string::npos);
    out.clear();
    assert(append_native_sm3_texturecube_sample(out,"r283_t1",0x5u,
        "r283_t0",3u,18u,NativeSm3Texture2DMode::Implicit,
        {},{},0x1bu));
    assert(out.find("r283_t1.xz = r283_cube_texel_18.wy;") != std::string::npos);
    out.clear();
    assert(append_native_sm3_texture3d_sample(out,"r283_t1",0xau,
        "r283_t0",4u,19u,NativeSm3Texture2DMode::ExplicitLod,
        {},{},0x1bu));
    assert(out.find("r283_t1.yw = r283_volume_texel_19.zx;") != std::string::npos);
    const auto saved = out;
    assert(!append_native_sm3_texture2d_sample(out,"r283_t1",0xfu,
        "r283_t0",2u,20u,NativeSm3Texture2DMode::Implicit,
        {},{},256u));
    assert(!append_native_sm3_texturecube_sample(out,"r283_t1",0xfu,
        "r283_t0",16u,21u,NativeSm3Texture2DMode::Implicit,
        {},{},0xe4u));
    assert(!append_native_sm3_texture3d_sample(out,"r283_t1",0xfu,
        "r283_t0",2u,22u,NativeSm3Texture2DMode::Gradients,
        {},{},0xe4u));
    assert(out == saved); // No partial source or silent native activation.
}
