// 01062: real game native GPU frame -> independent-size XR/theater consumer.
// Portable geometry/ownership gate; actual game and Quest3 remain UNTESTED.
#include "../../src/vr/d3d11/native_game_gpu_handoff.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeGpuHandoff;
int main() {
    constexpr auto accepts = GameNativeGpuHandoff::independent_gpu_frame_ready;
    // Native 4:3 menu and HD race surfaces can be handed to a consumer while
    // the desktop D3D9Ex renderer keeps its own 3440x1440 source/Present.
    assert(accepts(true, true, true, 3440,1440, 1440,1080, 1440,1080));
    assert(accepts(true, true, true, 3440,1440, 1920,1080, 1920,1080));
    assert(accepts(true, true, true, 1920,1080, 1920,1080, 1920,1080));
    // A guessed stale color source or unavailable mono permission cannot
    // publish either a mismatched or fabricated native eye frame.
    assert(!accepts(false,true,true, 3440,1440, 1440,1080, 1440,1080));
    assert(!accepts(true,false,true, 3440,1440, 1440,1080, 1440,1080));
    assert(!accepts(true,true,false, 3440,1440, 1440,1080, 1440,1080));
    assert(!accepts(true,true,true, 0,1440, 1440,1080, 1440,1080));
    assert(!accepts(true,true,true, 3440,0, 1440,1080, 1440,1080));
    assert(!accepts(true,true,true, 3440,1440, 0,1080, 0,1080));
    assert(!accepts(true,true,true, 3440,1440, 1440,0, 1440,0));
    assert(!accepts(true,true,true, 3440,1440, 1440,1080, 1920,1080));
    assert(!accepts(true,true,true, 3440,1440, 1440,1080, 1440,1440));
    // The existing same-size D3D9Ex desktop write requirement stays intact.
    assert(!GameNativeGpuHandoff::gpu_frame_output_ready(
        true, true, false, false));
    assert(GameNativeGpuHandoff::may_offer(
        true, true, true, true, true, true, 1440,1080, 7u));
}
