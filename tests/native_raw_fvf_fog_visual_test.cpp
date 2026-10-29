#include "src/vr/d3d11/native_game_raw_fvf_fog_visual.hpp"
#include <cassert>
#include <limits>
using outrun::vr::dx11::native_raw_fvf_fog_visual_admission;
using outrun::vr::dx11::native_raw_fvf_specular_fog_visual_admission;
int main() {
    const auto admitted = [](bool opt, bool state, unsigned table,
                            unsigned vertex, unsigned range, float start,
                            float end, float density) {
        return native_raw_fvf_fog_visual_admission(
            opt, state, table, vertex, range, start, end, density);
    };
    // Genuine fixed-function active table / vertex / range fog can produce
    // opt-in approximate RGB pixels, but NEVER a complete native scene.
    assert(admitted(true, true, 1u, 0u, 0u, 0.f, 1.f, 0.5f));
    assert(admitted(true, true, 0u, 2u, 1u, 0.f, 1.f, 0.5f));
    assert(admitted(true, true, 3u, 0u, 0u, 0.f, 1.f, 0.5f));
    assert(!admitted(false, true, 1u, 0u, 0u, 0.f, 1.f, 0.5f));
    assert(!admitted(true, false, 1u, 0u, 0u, 0.f, 1.f, 0.5f));
    assert(!admitted(true, true, 0u, 0u, 0u, 0.f, 1.f, 0.5f));
    assert(!admitted(true, true, 4u, 0u, 0u, 0.f, 1.f, 0.5f));
    assert(!admitted(true, true, 0u, 0xffffffffu, 0u, 0.f, 1.f, 0.5f));
    assert(!admitted(true, true, 1u, 0u, 2u, 0.f, 1.f, 0.5f));
    assert(!admitted(true, true, 3u, 0u, 0u, 2.f, 1.f, 0.5f));
    assert(!admitted(true, true, 0u, 3u, 1u, 1.f, 1.f, 0.5f));
    assert(!admitted(true, true, 1u, 0u, 0u, 0.f, 1.f, -0.1f));
    const auto spec = [](bool opt, bool query, bool fvf, bool enabled,
                         unsigned shade, unsigned table, unsigned vertex,
                         unsigned range, float start, float end, float density) {
        return native_raw_fvf_specular_fog_visual_admission(
            opt, query, fvf, enabled, shade, table, vertex,
            range, start, end, density);
    };
    assert(spec(true,true,true,true,2u,3u,0u,0u,0.f,1.f,1.f));
    assert(spec(true,true,true,true,2u,0u,2u,1u,0.f,1.f,0.2f));
    assert(!spec(false,true,true,true,2u,3u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,false,true,true,2u,3u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,true,false,true,2u,3u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,true,true,false,2u,3u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,true,true,true,1u,3u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,true,true,true,3u,3u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,true,true,true,2u,0u,0u,0u,0.f,1.f,1.f));
    assert(!spec(true,true,true,true,2u,3u,0u,0u,1.f,0.f,1.f));
    const float nan=(std::numeric_limits<float>::quiet_NaN)();
    const float inf=(std::numeric_limits<float>::infinity)();
    // EXP reads density only; stale unused START/END are immaterial.
    // This is the source-authentic 01154 equation consumed by new FVF PS.
    assert(admitted(true, true, 1u, 0u, 0u, nan, 1.f, 0.5f));
    assert(admitted(true, true, 1u, 0u, 0u, 0.f, inf, 0.5f));
    // LINEAR still consumes both endpoints: no unsafe native admission.
    assert(!admitted(true, true, 3u, 0u, 0u, nan, 1.f, 0.5f));
    assert(!admitted(true, true, 3u, 0u, 0u, 0.f, inf, 0.5f));
    assert(!admitted(true, true, 1u, 0u, 0u, 0.f, 1.f, inf));
    return 0;
}
