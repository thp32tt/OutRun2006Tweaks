// Real native D3D9 SM3 c# -> TEMP -> arithmetic -> IFC -> implicit TEX.
// The original D3D9 renderer remains fallback for varying/unknown origin.
#include "../src/vr/d3d11/native_sm3_temp_draw_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_derivative_uniformity.hpp"
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
namespace {
bool texture_allowed(const NativeSm3DerivativeUniformity& f) {
    return native_sm3_texture_mode_allowed_in_control_flow(
        NativeSm3Texture2DMode::Implicit, !f.implicit_sampling_safe());
}
}
int main() {
    constexpr NativeSm3TempDrawUniformity empty;
    static_assert(!empty.contains(0u, 1u));
    static_assert(!empty.contains(32u, 1u));
    NativeSm3TempDrawUniformity temps;
    temps.write(0u, 0x0fu, true, true); // MOV r0, c0, a live D3D9 draw constant
    assert(temps.contains(0u, 0x0fu));
    temps.write(1u, 0x03u, temps.contains(0u, 0x03u), true);
    assert(temps.contains(1u, 0x03u));
    assert(!temps.contains(1u, 0x04u)); // unwritten physical z rejected
    temps.write(1u, 0x08u, true, true);
    assert(temps.contains(1u, 0x0bu)); // x/y/w, not z
    NativeSm3DerivativeUniformity flow;
    assert(flow.begin(native_sm3_ifc_is_quad_uniform(
        temps.contains(1u, 1u) ? NativeSm3IfcScalarOrigin::DrawFloatConstant :
                                 NativeSm3IfcScalarOrigin::PixelDependent,
        NativeSm3IfcScalarOrigin::DrawFloatConstant)));
    assert(texture_allowed(flow));
    assert(flow.end());
    temps.write(1u, 0x01u, false, true); // MOV r1.x, input/vFace/texture-derived
    assert(!temps.contains(1u, 1u));
    assert(temps.contains(1u, 0x02u)); // y still a legitimate constant
    assert(flow.begin(false)); // a varying pixel IFC
    assert(!texture_allowed(flow));
    assert(flow.end());
    temps.write(1u, 0x02u, true, false); // pixel-varying branch write
    assert(!temps.contains(1u, 0x02u));
    temps.write(1u, 0x04u, true, false); // predicate/repeat/loop write
    assert(!temps.contains(1u, 0x04u));
    temps.write(1u, 0x08u, false, true); // native texture result, no provenance
    assert(!temps.contains(1u, 0x08u));
    temps.write(2u, 0x0fu, true, true);
    temps.invalidate(2u); // D3D9 SGN scratch register lifetime
    assert(!temps.contains(2u, 0x0fu));
    // A partial varying overwrite must poison only the written physical
    // channels, retaining independent c#-derived lanes for subsequent IFC.
    temps.write(3u, 0x0fu, true, true);
    temps.write(3u, 0x05u, false, true);
    assert(!temps.contains(3u, 0x01u));
    assert(!temps.contains(3u, 0x04u));
    assert(temps.contains(3u, 0x0au));
    assert(!temps.contains(3u, 0x0bu));
    // A predicated/structured overwrite cannot pretend to preserve
    // previously uniform content on a lane it may have modified.
    temps.write(3u, 0x02u, true, false);
    assert(!temps.contains(3u, 0x02u));
    assert(temps.contains(3u, 0x08u));
    // Invalid mask bits and out-of-range register IDs never become proof.
    assert(!temps.contains(3u, 0x10u));
    temps.write(32u, 0x0fu, true, true);
    assert(!temps.contains(32u, 0x0fu));
    temps.write(31u, 0x08u, true, true);
    assert(temps.contains(31u, 0x08u));
    assert(!temps.contains(31u, 0x01u));
    temps.invalidate(31u);
    assert(!temps.contains(31u, 0x08u));
    assert(flow.empty());
}
