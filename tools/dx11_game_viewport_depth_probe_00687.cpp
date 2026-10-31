#include "../src/vr/d3d11/live_game_viewport_depth.hpp"
#include <array>
#include <cassert>
#include <cmath>
#include <initializer_list>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
static bool close(float a, float b) { return std::fabs(a - b) < 1.0e-6f; }
int main() {
    // Live game object-space WVP clip depth -> D3D11 diagnostic frame.
    std::array<float, 4> world{1.f, -2.f, .25f, 2.f};
    assert(game_native_world_depth_clip(world, .2f, .8f));
    assert(close(world[2], .55f));
    assert(close(world[0], 1.f) && close(world[3], 2.f));
    std::array<float, 4> reverse{0.f, 0.f, .5f, 2.f};
    assert(game_native_world_depth_clip(reverse, 1.f, 0.f));
    assert(close(reverse[2], 1.5f));
    std::array<float, 4> constant{0.f, 0.f, .5f, 2.f};
    assert(game_native_world_depth_clip(constant, .4f, .4f));
    assert(close(constant[2], .8f));
    // Preserve signed W for hardware clipping at the race camera plane.
    std::array<float, 4> crossing{0.f, 0.f, -.6f, -1.f};
    assert(game_native_world_depth_clip(crossing, .25f, .75f));
    assert(close(crossing[2], -.55f) && close(crossing[3], -1.f));
    // D3D9 menu XYZRHW is already window depth, never map it twice.
    float screenZ = -123.f;
    assert(game_native_screen_depth_clip(.3f, 2.f, .2f, .8f, screenZ));
    assert(close(screenZ, .6f));
    const float untouched = screenZ;
    assert(!game_native_screen_depth_clip(.3f, 0.f, .2f, .8f, screenZ));
    assert(close(screenZ, untouched));
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    for (float invalid : {nan, inf, -inf, -0.01f, 1.01f}) {
        std::array<float, 4> data{1.f, 2.f, .25f, 2.f};
        assert(!game_native_world_depth_clip(data, invalid, 1.f));
        assert(close(data[2], .25f));
        assert(!game_native_screen_depth_clip(.3f, 1.f, 0.f, invalid, screenZ));
        assert(close(screenZ, untouched));
    }
    std::array<float, 4> bad{1.f, 2.f, inf, 2.f};
    assert(!game_native_world_depth_clip(bad, 0.f, 1.f));
    std::array<float, 4> over{0.f, 0.f, -3.e38f, 3.e38f};
    assert(!game_native_world_depth_clip(over, 1.f, 0.f));
    assert(!game_native_screen_depth_clip(inf, 1.f, 0.f, 1.f, screenZ));
}
