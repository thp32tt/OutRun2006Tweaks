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
    // For all four D3D9 Z-write/comparison combinations the native OM
    // descriptor selected for creation is the one actually bound to Draw.
    using outrun::vr::dx11::live_game_frame::game_native_depth_slot;
    for (unsigned slot = 0u; slot < 4u; ++slot) {
        assert(game_native_depth_slot((slot & 2u) != 0u,
                                      (slot & 1u) != 0u) == slot);
    }
    assert(game_native_depth_slot(false, false) !=
           game_native_depth_slot(true, false));
    assert(game_native_depth_slot(false, true) !=
           game_native_depth_slot(true, true));
    // D3D9 menu/sky ALWAYS comparison admits both native Z-write modes.
    assert(game_native_depth_admission(1,1,8,0,0,true,depth));
    assert(depth.enabled && depth.always && depth.writeEnabled && !depth.lessEqual);
    assert(game_native_depth_admission(1,0,8,0,0,true,depth));
    assert(depth.enabled && depth.always && !depth.writeEnabled);
    assert(game_native_depth_admission(1,1,2,0,0,true,depth));
    assert(!depth.always && depth.writeEnabled && !depth.lessEqual);
    // EQUAL/NOTEQUAL preserve independent read-only and depth-writing DSVs.
    using outrun::vr::dx11::live_game_frame::game_native_depth_equality_slot;
    for (unsigned compare : {3u, 6u}) {
        for (unsigned write : {0u, 1u}) {
            assert(game_native_depth_admission(1,write,compare,0,0,true,depth));
            assert(depth.enabled && depth.equalityMode == compare &&
                   !depth.always && depth.writeEnabled == (write != 0u));
            assert(game_native_depth_equality_slot(write != 0u, compare) ==
                   (write ? 2u : 0u) + (compare == 6u ? 1u : 0u));
        }
    }
    assert(game_native_depth_equality_slot(false, 3u) !=
           game_native_depth_equality_slot(false, 6u));
    assert(game_native_depth_equality_slot(true, 3u) !=
           game_native_depth_equality_slot(false, 3u));
    assert(!game_native_depth_admission(1,1,3,0,0,false,depth));
    assert(!game_native_depth_admission(1,0,6,1,0,true,depth));
    assert(game_native_depth_admission(1,1,8,0,0,true,depth));
    assert(depth.equalityMode == 0u && depth.always);
    assert(!game_native_depth_admission(1,1,8,0,0,false,depth));
    assert(!game_native_depth_admission(1,2,8,0,0,true,depth));
    const auto retained = depth;
    for (unsigned mode : {2u, 3u, 0xffffffffu})
        assert(!game_native_depth_admission(mode,1,4,0,0,true,depth));
    assert(!game_native_depth_admission(1,2,4,0,0,true,depth));
    for (unsigned unsupported : {1u, 5u, 7u, 9u})
        assert(!game_native_depth_admission(1,1,unsupported,0,0,true,depth));
    assert(!game_native_depth_admission(1,1,4,1,0,true,depth));
    assert(!game_native_depth_admission(1,1,4,0,0x3f800000u,true,depth));
    assert(!game_native_depth_admission(1,1,4,0,0,false,depth));
    assert(depth.enabled == retained.enabled &&
           depth.lessEqual == retained.lessEqual &&
           depth.writeEnabled == retained.writeEnabled &&
           depth.always == retained.always &&
           depth.equalityMode == retained.equalityMode);
    assert(game_native_depth_admission(1,1,4,0x80000000u,
                                       0x80000000u,true,depth));
    return 0;
}
