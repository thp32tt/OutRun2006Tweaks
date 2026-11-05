// Authentic D3D9 ps_3_0 IF/ELSE -> TEMP -> IFC -> TEXLD Draw coverage.
#include "../src/vr/d3d11/native_sm3_temp_draw_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    constexpr auto C = NativeSm3IfcScalarOrigin::DrawFloatConstant;
    constexpr auto V = NativeSm3IfcScalarOrigin::PixelDependent;
    NativeSm3TempDrawUniformity t;
    NativeSm3DerivativeUniformity flow;
    assert(!t.contains(0, 3));
    assert(t.begin_if(true) && flow.begin(true));
    t.write(0, 3, true, true);
    assert(t.otherwise() && !t.contains(0, 3));
    t.write(0, 3, true, true);
    assert(t.end_if() && flow.end() && t.contains(0, 3));
    assert(native_sm3_ifc_is_quad_uniform(C, C));
    assert(flow.begin(native_sm3_ifc_is_quad_uniform(C, C)));
    assert(native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit, !flow.implicit_sampling_safe()));
    std::string shader;
    assert(append_native_sm3_texture2d_sample(
        shader, "r283_color", 15u, "r283_t0", 0u, 9u,
        NativeSm3Texture2DMode::Implicit));
    assert(shader.find(".Sample(") != std::string::npos && flow.end());
    assert(t.begin_if(true));
    t.write(1, 1, true, true);
    assert(t.end_if() && !t.contains(1, 1)); // missing ELSE
    t.write(2, 3, true, true);
    assert(t.begin_if(false) && flow.begin(false));
    assert(!t.uniform_flow() && !flow.implicit_sampling_safe());
    t.write(2, 1, true, true);
    assert(t.otherwise());
    t.write(2, 2, true, true);
    assert(t.end_if() && flow.end() && !t.contains(2, 3));
    assert(!native_sm3_ifc_is_quad_uniform(V, C));
    assert(t.begin_if(true) && t.begin_if(false));
    t.write(3, 1, true, true);
    assert(t.otherwise());
    t.write(3, 1, true, true);
    assert(t.end_if() && t.end_if() && !t.contains(3, 1));
    t.write(4, 7, true, true);
    assert(t.begin_loop() && !t.uniform_flow());
    t.write(4, 2, true, true);
    assert(t.begin_if(true));
    t.write(5, 1, true, true);
    assert(t.otherwise());
    t.write(5, 1, true, true);
    assert(t.end_if() && t.end_loop());
    assert(!t.contains(4, 2) && t.contains(4, 5) && !t.contains(5, 1));
    assert(t.empty() && flow.empty());
    assert(!t.otherwise() && !t.end_if() && !t.end_loop());
}
