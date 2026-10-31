#include "../src/vr/d3d11/native_game_partial_color_replay.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    // D3D11.0 after actual game-authored clipped TARGET|Z accepts only
    // paired color + depth GPU work. Never silently replay color alone.
    assert(partial_game_paired_target_depth_raster(false,true,true,true));
    assert(!partial_game_paired_target_depth_raster(false,true,true,false));
    assert(!partial_game_paired_target_depth_raster(false,true,false,true));
    assert(!partial_game_paired_target_depth_raster(false,false,true,true));
    assert(!partial_game_paired_target_depth_raster(true,true,true,true));
    // D3D11.1 continues through both scoped ClearView mutations.
    assert(partial_game_color_replay_route(true,false,true) ==
           PartialColorReplayRoute::clear_view);
    // An unsupported D3D11.0 partial depth cannot be silently color-only.
    assert(partial_game_color_replay_route(false,false,true) ==
           PartialColorReplayRoute::reject);
}
