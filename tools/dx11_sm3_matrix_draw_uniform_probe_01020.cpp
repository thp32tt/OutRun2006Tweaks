// Game VS/PS SM3 immutable matrix c# + uniform vector -> TEMP -> IFC
// -> native implicit sample; negative cases preserve original D3D9Ex.
#include "../src/vr/d3d11/native_sm3_temp_draw_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_constant_codegen.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <array>
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    static_assert(native_sm3_matrix_draw_uniform(4, 4, 0x0f, true));
    static_assert(native_sm3_matrix_draw_uniform(3, 4, 0x07, true));
    static_assert(native_sm3_matrix_draw_uniform(4, 3, 0x08, true));
    static_assert(native_sm3_matrix_draw_uniform(3, 3, 0x03, true));
    static_assert(native_sm3_matrix_draw_uniform(2, 3, 0x02, true));
    static_assert(!native_sm3_matrix_draw_uniform(4, 4, 0x0f, false));
    static_assert(!native_sm3_matrix_draw_uniform(4, 4, 0x10, true));
    static_assert(!native_sm3_matrix_draw_uniform(2, 4, 0x03, true));
    static_assert(!native_sm3_matrix_draw_uniform(4, 2, 0x0f, true));
    static_assert(!native_sm3_matrix_draw_uniform(3, 3, 0u, true));

    const std::array<std::string, 4> rows{
        {"r283_c[0]", "r283_def1", "r283_c[2]", "r283_c[3]"}};
    std::string shader;
    assert(append_native_sm3_matrix(shader, "r283_t1", 0x0f,
                                    "r283_t0", rows, 4, 37, 4));
    assert(shader.find("dot((r283_t0).xyzw, (r283_c[0]).xyzw)") !=
           std::string::npos);
    assert(shader.find("dot((r283_t0).xyzw, (r283_def1).xyzw)") !=
           std::string::npos);
    assert(shader.find("r283_t1.xyzw = r283_matrix_37.xyzw") !=
           std::string::npos);
    assert(!append_native_sm3_matrix(shader, "r283_t1", 0x10,
                                     "r283_t0", rows, 4, 38, 4));
    for (const auto shape : std::array<std::array<unsigned, 3>, 4>{{
             {{3u, 4u, 7u}}, {{4u, 3u, 15u}},
             {{3u, 3u, 7u}}, {{2u, 3u, 3u}} }}) {
        assert(append_native_sm3_matrix(shader, "r283_t2", shape[2],
                                        "r283_t0", rows, shape[0],
                                        40u + shape[0], shape[1]));
    }
    NativeSm3TempDrawUniformity temps;
    temps.write(0u, 0x0fu, true, true); // original c# uniform vector
    assert(temps.contains(0u, 0x0fu));
    // The parser requires both the physical vector lanes and actual
    // constant rows; a matrix output can now feed the uniform IFC.
    temps.write(1u, 0x0fu,
                temps.contains(0u, 0x0fu) &&
                native_sm3_matrix_draw_uniform(4, 4, 0x0fu, true), true);
    assert(temps.contains(1u, 0x0fu));
    NativeSm3DerivativeUniformity flow;
    assert(flow.begin(native_sm3_ifc_is_quad_uniform(
        temps.contains(1u, 1u) ? NativeSm3IfcScalarOrigin::DrawFloatConstant :
                                 NativeSm3IfcScalarOrigin::PixelDependent,
        NativeSm3IfcScalarOrigin::DrawFloatConstant)));
    assert(native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit, !flow.implicit_sampling_safe()));
    assert(append_native_sm3_texture2d_sample(
        shader, "r283_color", 15u, "r283_t0", 0u, 50u,
        NativeSm3Texture2DMode::Implicit));
    assert(shader.find(".Sample(") != std::string::npos);
    assert(flow.end());

    temps.write(1u, 0x01u, false, true); // pixel input overwrites IFC x
    assert(!temps.contains(1u, 0x01u));
    assert(temps.contains(1u, 0x0eu)); // unaffected uniform yzw survive
    assert(flow.begin(false));
    assert(!native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit, !flow.implicit_sampling_safe()));
    assert(flow.end());
    temps.write(2u, 15u, true, true);
    temps.write(2u, 15u, native_sm3_matrix_draw_uniform(4, 4, 15u, false), true);
    assert(!temps.contains(2u, 15u)); // dynamic relative c[aL]/c[a0] row
    temps.write(2u, 3u, true, false); // predicated/loop/IF matrix write
    assert(!temps.contains(2u, 3u));
    temps.write(3u, 15u, false, true); // varying vector input to M4x4
    assert(!temps.contains(3u, 1u));
    assert(flow.empty());
}
