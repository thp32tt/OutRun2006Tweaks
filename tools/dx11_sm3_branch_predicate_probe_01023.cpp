// Live ps_3_0 IF/IFC -> SETP p0 (both arms) -> implicit
// TEXLD/TEXLDP/TEXLDB -> native D3D11 game Draw/DrawIndexed.
#include "../src/vr/d3d11/native_sm3_predicate_flow.hpp"
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include "../src/vr/d3d11/native_sm3_predicated_instruction.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    constexpr auto C = NativeSm3IfcScalarOrigin::DrawFloatConstant;
    constexpr auto V = NativeSm3IfcScalarOrigin::PixelDependent;
    NativeSm3DrawUniformPredicate p0;
    NativeSm3PredicateFlow initialized;
    NativeSm3DerivativeUniformity gradients;
    assert(!p0.implicit_sampling_safe(true) && p0.implicit_sampling_safe(false));
    assert(p0.begin_if(true) && initialized.begin_if() && gradients.begin(true));
    assert(p0.uniform_flow());
    p0.write(native_sm3_ifc_is_quad_uniform(C, C), p0.uniform_flow());
    initialized.write();
    assert(p0.otherwise() && initialized.otherwise());
    assert(!p0.implicit_sampling_safe(true)); // entry was uninitialized
    p0.write(true, p0.uniform_flow());
    initialized.write();
    assert(p0.end_if() && initialized.end_if() && gradients.end());
    assert(p0.empty() && initialized.ready() && p0.implicit_sampling_safe(true));
    assert(native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit,
        !p0.implicit_sampling_safe(true) || !gradients.implicit_sampling_safe()));
    std::string source;
    assert(append_native_sm3_setp(source, "r283_c[0].x > r283_c[1].x"));
    assert(append_native_sm3_predicated_begin(source, false));
    assert(append_native_sm3_texture2d_sample(
        source, "r283_color", 15u, "r283_t0", 0u, 4u,
        NativeSm3Texture2DMode::Implicit));
    append_native_sm3_predicated_end(source);
    assert(source.find("if (r283_p0)") != std::string::npos);
    assert(source.find(".Sample(") != std::string::npos);
    // Uniform nested decisions permit a fully initialized p0 to feed TEX.
    NativeSm3DrawUniformPredicate nested;
    assert(nested.begin_if(true) && nested.begin_if(true));
    nested.write(true, nested.uniform_flow());
    assert(nested.otherwise());
    nested.write(true, nested.uniform_flow());
    assert(nested.end_if());
    assert(nested.otherwise());
    nested.write(true, nested.uniform_flow());
    assert(nested.end_if() && nested.implicit_sampling_safe(true));
    // A varying IFC selects different p0 values across pixels. Joining both
    // individually uniform SETP arms must NOT admit native implicit TEX.
    NativeSm3DrawUniformPredicate varying;
    assert(varying.begin_if(native_sm3_ifc_is_quad_uniform(V, C)));
    varying.write(true, varying.uniform_flow());
    assert(varying.otherwise());
    varying.write(true, varying.uniform_flow());
    assert(varying.end_if() && !varying.implicit_sampling_safe(true));
    assert(!native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit, !varying.implicit_sampling_safe(true)));
    assert(native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::ExplicitLod, !varying.implicit_sampling_safe(true)));
    // A missing ELSE must not manufacture a previously unwritten p0.
    NativeSm3DrawUniformPredicate missing;
    assert(missing.begin_if(true));
    missing.write(true, missing.uniform_flow());
    assert(missing.end_if() && !missing.implicit_sampling_safe(true));
    // Preinitialized uniform p0 surviving an untouched varying branch is safe.
    NativeSm3DrawUniformPredicate untouched;
    untouched.write(true, true);
    assert(untouched.begin_if(false) && untouched.end_if());
    assert(untouched.implicit_sampling_safe(true));
    // A divergent branch rewriting p0 destroys that provenance.
    assert(untouched.begin_if(false));
    untouched.write(true, untouched.uniform_flow());
    assert(untouched.end_if() && !untouched.implicit_sampling_safe(true));
    // A REP/LOOP with a SETP or BREAK cannot escape as uniform p0.
    NativeSm3DrawUniformPredicate loop;
    loop.write(true, true);
    assert(loop.begin_loop() && !loop.uniform_flow());
    loop.write(true, loop.uniform_flow());
    assert(loop.end_loop() && !loop.implicit_sampling_safe(true));
    loop.write(true, true);
    assert(loop.begin_loop() && loop.end_loop() &&
           loop.implicit_sampling_safe(true)); // untouched p0
    assert(!loop.end_loop() && !loop.end_if() && !loop.otherwise());
    assert(loop.empty() && nested.empty() && varying.empty() &&
           missing.empty() && untouched.empty());
}
