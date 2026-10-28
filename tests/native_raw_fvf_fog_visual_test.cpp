#include "src/vr/d3d11/native_game_raw_fvf_fog_visual.hpp"
#include <cassert>
#include <limits>
using outrun::vr::dx11::native_raw_fvf_fog_visual_admission;
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
    const float nan=(std::numeric_limits<float>::quiet_NaN)();
    const float inf=(std::numeric_limits<float>::infinity)();
    assert(!admitted(true, true, 1u, 0u, 0u, nan, 1.f, 0.5f));
    assert(!admitted(true, true, 1u, 0u, 0u, 0.f, inf, 0.5f));
    assert(!admitted(true, true, 1u, 0u, 0u, 0.f, 1.f, inf));
    return 0;
}
