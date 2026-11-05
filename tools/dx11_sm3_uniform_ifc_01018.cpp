// Real OutRun D3D9 SM3 IFC(c#,c#) -> native D3D11 PS gradient sampling.
// Mixed pixel-varying/temporary/vFace or nested varying IFC must fail closed.
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>

using namespace outrun::vr::dx11;
namespace {
constexpr auto C = NativeSm3IfcScalarOrigin::DrawFloatConstant;
constexpr auto V = NativeSm3IfcScalarOrigin::PixelDependent;
bool texture_allowed(const NativeSm3DerivativeUniformity& f,
                     NativeSm3Texture2DMode mode) {
    return native_sm3_texture_mode_allowed_in_control_flow(
        mode, !f.implicit_sampling_safe());
}
}
int main() {
    static_assert(native_sm3_ifc_is_quad_uniform(C, C));
    static_assert(!native_sm3_ifc_is_quad_uniform(C, V));
    static_assert(!native_sm3_ifc_is_quad_uniform(V, C));
    static_assert(!native_sm3_ifc_is_quad_uniform(V, V));
    NativeSm3DerivativeUniformity f;
    assert(f.begin(native_sm3_ifc_is_quad_uniform(C, C)));
    assert(texture_allowed(f, NativeSm3Texture2DMode::Implicit));
    assert(texture_allowed(f, NativeSm3Texture2DMode::Projected));
    assert(texture_allowed(f, NativeSm3Texture2DMode::Bias));
    assert(f.begin(true)); // Both IF b# and IFC(c#,c#) stay per-Draw uniform.
    assert(texture_allowed(f, NativeSm3Texture2DMode::Implicit));
    assert(f.end());
    assert(f.begin(native_sm3_ifc_is_quad_uniform(V, C)));
    assert(!texture_allowed(f, NativeSm3Texture2DMode::Implicit));
    assert(!texture_allowed(f, NativeSm3Texture2DMode::Projected));
    assert(!texture_allowed(f, NativeSm3Texture2DMode::Bias));
    assert(texture_allowed(f, NativeSm3Texture2DMode::ExplicitLod));
    assert(texture_allowed(f, NativeSm3Texture2DMode::Gradients));
    assert(f.begin(native_sm3_ifc_is_quad_uniform(C, C)));
    assert(!texture_allowed(f, NativeSm3Texture2DMode::Implicit));
    assert(f.end());
    assert(f.end());
    assert(texture_allowed(f, NativeSm3Texture2DMode::Implicit));
    assert(f.end());
    assert(f.empty());
    assert(!f.end()); // Unbalanced control flow rejected.
}
