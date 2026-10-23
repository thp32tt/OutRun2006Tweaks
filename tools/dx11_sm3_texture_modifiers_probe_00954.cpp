#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include "../src/vr/d3d11/native_sm3_arithmetic_codegen.hpp"
#include <cassert>
#include <string>

using namespace outrun::vr::dx11;

// All real TEXLD family source modifiers are accepted for float coordinates
// and gradients, but never for sampler slots or absent operands.
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Implicit, 0u, 1u));
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Projected, 0u, 11u));
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Bias, 0u, 12u));
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::ExplicitLod, 0u, 9u));
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Gradients, 2u, 1u));
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Gradients, 3u, 10u));
static_assert(native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Gradients, 1u, 0u));
static_assert(!native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Gradients, 1u, 1u));
static_assert(!native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Implicit, 2u, 0u));
static_assert(!native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::ExplicitLod, 3u, 11u));
static_assert(!native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Projected, 0u, 13u));
static_assert(!native_sm3_texture_modifier_supported(NativeSm3Texture2DMode::Gradients, 2u, 15u));
// A read of logical xy+w with swizzle wzyx requires physical x,z,w;
// a read of xy+z (gradient DZ) requires physical y,z,w.
static_assert(native_sm3_swizzled_components(
    native_sm3_source_modifier_components(
        native_sm3_texture_source_components(NativeSm3Texture2DMode::Implicit, 0u),
        10u), 0x1bu) == 0x0du);
static_assert(native_sm3_swizzled_components(
    native_sm3_source_modifier_components(
        native_sm3_texture_source_components(NativeSm3Texture2DMode::Gradients, 2u),
        9u), 0x1bu) == 0x0eu);

int main() {
    std::string coord = "r283_t0.xyzw";
    assert(append_native_sm3_source_modifier(coord, 1u));
    assert(coord == "-(r283_t0.xyzw)");
    std::string out;
    assert(append_native_sm3_texture2d_declarations(out, 3u));
    assert(append_native_sm3_texture2d_sample(
        out, "r283_t1", 0x03u, coord, 3u, 1u));
    assert(out.find("r283_texture3.Sample(r283_sampler3, (-(r283_t0.xyzw)).xy)") != std::string::npos);
    assert(out.find("r283_t1.xy = r283_texel_1.xy;") != std::string::npos);

    std::string projected = "input.r0.wzyx";
    assert(append_native_sm3_source_modifier(projected, 11u));
    assert(append_native_sm3_texture2d_sample(
        out, "r283_t1", 0x0fu, projected, 3u, 2u,
        NativeSm3Texture2DMode::Projected));
    assert(out.find(".xy / (abs(input.r0.wzyx)).w") != std::string::npos);

    std::string biased = "input.r0.xyzw";
    assert(append_native_sm3_source_modifier(biased, 2u));
    assert(append_native_sm3_texture2d_sample(
        out, "r283_t1", 0x0fu, biased, 3u, 3u,
        NativeSm3Texture2DMode::Bias));
    assert(out.find(".SampleBias(") != std::string::npos);
    assert(out.find(" - 0.5f") != std::string::npos);

    std::string lod = "r283_t2.xyzw";
    assert(append_native_sm3_source_modifier(lod, 9u));
    assert(append_native_sm3_texture2d_sample(
        out, "r283_t1", 0x07u, lod, 3u, 4u,
        NativeSm3Texture2DMode::ExplicitLod));
    assert(out.find(".SampleLevel(") != std::string::npos);
    assert(out.find(".zzzz") != std::string::npos);

    std::string gx = "r283_t3.xyzw", gy = "r283_t4.xyzw";
    assert(append_native_sm3_source_modifier(gx, 12u));
    assert(append_native_sm3_source_modifier(gy, 1u));
    assert(append_native_sm3_texture2d_sample(
        out, "r283_t1", 0x0fu, "input.r0.xyzw", 3u, 5u,
        NativeSm3Texture2DMode::Gradients, gx, gy));
    assert(out.find(".SampleGrad(") != std::string::npos);
    assert(out.find("-abs(r283_t3.xyzw)") != std::string::npos);
    assert(out.find("-(r283_t4.xyzw)") != std::string::npos);

    std::string invalid = "r283_t4.xyzw";
    assert(!append_native_sm3_source_modifier(invalid, 13u));
    assert(invalid == "r283_t4.xyzw");
    std::string rejected = out;
    assert(!append_native_sm3_texture2d_sample(
        rejected, "r283_t1", 0x0fu, coord, 3u, 6u,
        NativeSm3Texture2DMode::Gradients)); // missing gradients
    assert(rejected == out);
    assert(!append_native_sm3_texture2d_sample(
        rejected, "r283_t1", 0x0fu, coord, 16u, 6u));
    assert(rejected == out);
}
