// Compiled SM3 D3D9 b# IF -> native GPU TEXLD derivative admission.
// All pixel-varying IFC/predicated modes still fall back to original D3D9.
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>
using namespace outrun::vr::dx11;

static bool texture_ready(NativeSm3DerivativeUniformity& flow,
                          NativeSm3Texture2DMode mode, bool predicated=false) {
    return native_sm3_texture_mode_allowed_in_control_flow(
        mode, predicated || !flow.implicit_sampling_safe());
}
int main() {
    NativeSm3DerivativeUniformity f;
    assert(texture_ready(f, NativeSm3Texture2DMode::Implicit));
    assert(f.begin(true)); // D3D9 b# or immutable DEFB
    assert(texture_ready(f, NativeSm3Texture2DMode::Implicit));
    assert(texture_ready(f, NativeSm3Texture2DMode::Projected));
    assert(texture_ready(f, NativeSm3Texture2DMode::Bias));
    assert(!texture_ready(f, NativeSm3Texture2DMode::Implicit, true));
    assert(f.begin(true));
    assert(texture_ready(f, NativeSm3Texture2DMode::Implicit));
    assert(f.end());
    assert(f.begin(false)); // D3D9 IFC real pixel-varying operand
    assert(!texture_ready(f, NativeSm3Texture2DMode::Implicit));
    assert(!texture_ready(f, NativeSm3Texture2DMode::Projected));
    assert(!texture_ready(f, NativeSm3Texture2DMode::Bias));
    assert(texture_ready(f, NativeSm3Texture2DMode::ExplicitLod));
    assert(texture_ready(f, NativeSm3Texture2DMode::Gradients));
    assert(f.begin(true)); // Nested bool cannot erase varying outer condition.
    assert(!texture_ready(f, NativeSm3Texture2DMode::Implicit));
    assert(f.end());
    assert(f.end());
    assert(texture_ready(f, NativeSm3Texture2DMode::Implicit));
    assert(f.end());
    assert(f.empty());
    assert(!f.end());
    for (int i = 0; i < 8; ++i) assert(f.begin(true));
    assert(!f.begin(true)); // Unsupported nesting stays fail-closed.
    assert(texture_ready(f, NativeSm3Texture2DMode::Implicit));
    for (int i = 0; i < 8; ++i) assert(f.end());
    assert(f.empty());
}
