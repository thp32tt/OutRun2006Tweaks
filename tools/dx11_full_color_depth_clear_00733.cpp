#include "../src/vr/d3d11/native_game_full_color_depth.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameNativeFrameBatch b{};
    b.succeeded(true); b.record_source_draw(0);
    b.reset(); // Successful whole color Clear replaces the prior scene.
    assert(GameNativeFullColorDepthClear::can_mirror(true,false,true,0.325f));
    b.note_full_depth_clear(0.325f);
    assert(b.accepts_full(0) && b.clear_depth());
    assert(b.depth_clear_value(false) == 0.325f);
    assert(b.depth_clear_value(true) == 0.325f);
    b.consume_depth_clear(); b.succeeded(true); b.record_source_draw(0);
    assert(b.publishable_full(true,1));
    assert(!GameNativeFullColorDepthClear::can_mirror(false,false,true,0.325f));
    assert(!GameNativeFullColorDepthClear::can_mirror(true,true,true,0.325f));
    assert(!GameNativeFullColorDepthClear::can_mirror(true,false,false,0.325f));
    assert(!GameNativeFullColorDepthClear::can_mirror(true,false,true,-0.1f));
    assert(!GameNativeFullColorDepthClear::can_mirror(true,false,true,1.1f));
    assert(!GameNativeFullColorDepthClear::can_mirror(
        true,false,true,std::numeric_limits<float>::quiet_NaN()));
    b.reset();
    if (!GameNativeFullColorDepthClear::can_mirror(true,true,true,0.325f)) b.abort();
    assert(b.stopped && !b.publishable_full(true,0));
    b.reset(); // TARGET-only Clear remains legal with default native depth.
    assert(b.accepts_full(0) && !b.depthClearPending);
    return 0;
}
