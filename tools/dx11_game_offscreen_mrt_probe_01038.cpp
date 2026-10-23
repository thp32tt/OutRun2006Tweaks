#include "src/vr/d3d11/native_game_offscreen_mrt.hpp"
using outrun::vr::dx11::native_game_offscreen_mrt_slot_compatible;
int main() {
    // Positive: camera MRT1 shares the exact physical raster/multisample
    // configuration with MRT0, but it may use its own independent format.
    if (!native_game_offscreen_mrt_slot_compatible(
            3440,1440,1,0,3440,1440,1,0,true,true,true)) return 1;
    if (!native_game_offscreen_mrt_slot_compatible(
            1280,720,4,2,1280,720,4,2,true,true,true)) return 2;
    // Negative: do not attribute wrong-size, wrong-MSAA, foreign/shared,
    // or XR-eye/depth MRT writes to game-owned pixel source chronology.
    if (native_game_offscreen_mrt_slot_compatible(
            3440,1440,1,0,256,144,1,0,true,true,true)) return 3;
    if (native_game_offscreen_mrt_slot_compatible(
            1280,720,4,2,1280,720,1,0,true,true,true)) return 4;
    if (native_game_offscreen_mrt_slot_compatible(
            1280,720,4,2,1280,720,4,1,true,true,true)) return 5;
    if (native_game_offscreen_mrt_slot_compatible(
            1280,720,4,2,1280,720,4,2,false,true,true)) return 6;
    if (native_game_offscreen_mrt_slot_compatible(
            1280,720,4,2,1280,720,4,2,true,false,true)) return 7;
    if (native_game_offscreen_mrt_slot_compatible(
            1280,720,4,2,1280,720,4,2,true,true,false)) return 8;
    return 0;
}
