#include "../src/vr/d3d11/live_game_depth_state.hpp"
#include <cassert>
#include <initializer_list>
using outrun::vr::dx11::live_game_frame::GameNativeDepthAdmission;
using outrun::vr::dx11::live_game_frame::game_native_depth_admission;
int main() {
    GameNativeDepthAdmission depth{true, true, true};
    assert(game_native_depth_admission(0,0,0,0,0,false,depth));
    assert(!depth.enabled && !depth.lessEqual && !depth.writeEnabled);
    assert(game_native_depth_admission(1,1,2,0,0,true,depth));
    assert(depth.enabled && !depth.lessEqual && depth.writeEnabled);
    assert(game_native_depth_admission(1,1,4,0,0,true,depth));
    assert(depth.enabled && depth.lessEqual && depth.writeEnabled);
    // Game-authored Z-read-only menu/race overlays must keep real D3D11
    // LESS/LESS_EQUAL tests without contaminating subsequent depth draws.
    assert(game_native_depth_admission(1,0,2,0,0,true,depth));
    assert(depth.enabled && !depth.lessEqual && !depth.writeEnabled);
    assert(game_native_depth_admission(1,0,4,0,0,true,depth));
    assert(depth.enabled && depth.lessEqual && !depth.writeEnabled);
    assert(game_native_depth_admission(1,1,4,0,0,true,depth));
    const auto retained = depth;
    for (unsigned mode : {2u, 3u, 0xffffffffu})
        assert(!game_native_depth_admission(mode,1,4,0,0,true,depth));
    assert(!game_native_depth_admission(1,2,4,0,0,true,depth));
    assert(!game_native_depth_admission(1,1,5,0,0,true,depth));
    assert(!game_native_depth_admission(1,1,4,1,0,true,depth));
    assert(!game_native_depth_admission(1,1,4,0,0x3f800000u,true,depth));
    assert(!game_native_depth_admission(1,1,4,0,0,false,depth));
    assert(depth.enabled == retained.enabled &&
           depth.lessEqual == retained.lessEqual &&
           depth.writeEnabled == retained.writeEnabled);
    assert(game_native_depth_admission(1,1,4,0x80000000u,
                                       0x80000000u,true,depth));
    return 0;
}
