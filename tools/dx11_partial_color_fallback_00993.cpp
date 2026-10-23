#include "../src/vr/d3d11/native_game_partial_color_replay.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    // Real menu/vehicle partial TARGET clear + ColorFill: exact GPU raster
    // on D3D11.0; regular ClearView remains the D3D11.1 fast path.
    assert(partial_game_color_replay_route(false, true, true) ==
           PartialColorReplayRoute::raster);
    assert(partial_game_color_replay_route(true, true, true) ==
           PartialColorReplayRoute::clear_view);
    // Combined Z and unknown native RTV must never publish color-only output.
    assert(partial_game_color_replay_route(false, false, true) ==
           PartialColorReplayRoute::reject);
    assert(partial_game_color_replay_route(false, true, false) ==
           PartialColorReplayRoute::reject);
    // A combined Z write is still valid when D3D11.1 handles both operations.
    assert(partial_game_color_replay_route(true, false, true) ==
           PartialColorReplayRoute::clear_view);
    return 0;
}
