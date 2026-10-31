// Authentic game SM3 SETP -> draw-uniform p0 -> native predicated
// TEXLD/TEXLDP/TEXLDB. Pixel-varying and conditional SETP fail closed.
#include "../src/vr/d3d11/native_sm3_predicate_flow.hpp"
#include "../src/vr/d3d11/native_sm3_predicated_instruction.hpp"
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>
#include <initializer_list>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    constexpr auto C = NativeSm3IfcScalarOrigin::DrawFloatConstant;
    constexpr auto V = NativeSm3IfcScalarOrigin::PixelDependent;
    NativeSm3DrawUniformPredicate provenance;
    NativeSm3PredicateFlow p0;
    NativeSm3DerivativeUniformity flow;
    assert(!provenance.implicit_sampling_safe(true)); // unwritten p0
    assert(provenance.implicit_sampling_safe(false)); // unpredicated TEX
    provenance.write(native_sm3_ifc_is_quad_uniform(C, C), true);
    p0.write();
    assert(p0.ready() && provenance.implicit_sampling_safe(true));
    assert(flow.begin(true)); // immutable b# live IF
    for (auto mode : {NativeSm3Texture2DMode::Implicit,
                      NativeSm3Texture2DMode::Projected,
                      NativeSm3Texture2DMode::Bias})
        assert(native_sm3_texture_mode_allowed_in_control_flow(
            mode, !provenance.implicit_sampling_safe(true) ||
                      !flow.implicit_sampling_safe()));
    std::string shader;
    assert(append_native_sm3_setp(shader, "r283_c[3].x >= r283_t0.y"));
    assert(append_native_sm3_predicated_begin(shader, false));
    assert(append_native_sm3_texture2d_sample(
        shader, "r283_color", 15u, "r283_t0", 0u, 9u,
        NativeSm3Texture2DMode::Implicit));
    append_native_sm3_predicated_end(shader);
    assert(shader.find("r283_p0 = (") != std::string::npos);
    assert(shader.find("if (r283_p0)") != std::string::npos);
    assert(shader.find(".Sample(") != std::string::npos);
    assert(flow.end());
    provenance.write(native_sm3_ifc_is_quad_uniform(V, C), true);
    assert(p0.ready() && !provenance.implicit_sampling_safe(true));
    assert(!native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit,
        !provenance.implicit_sampling_safe(true)));
    assert(native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::ExplicitLod,
        !provenance.implicit_sampling_safe(true)));
    assert(native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Gradients,
        !provenance.implicit_sampling_safe(true)));
    provenance.write(true, false); // SETP in divergent/conditional flow
    assert(!provenance.implicit_sampling_safe(true));
    provenance.write(true, true); // later unconditional SETP restores state
    assert(flow.begin(false));
    assert(!native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit,
        !provenance.implicit_sampling_safe(true) ||
        !flow.implicit_sampling_safe()));
    assert(flow.end() && flow.empty());
    provenance.write(true, false); // later varying SETP poisons state
    assert(!provenance.implicit_sampling_safe(true));
}
