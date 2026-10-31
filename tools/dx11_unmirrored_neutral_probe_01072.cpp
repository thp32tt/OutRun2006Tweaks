#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_scissor_clip.hpp"
#include <cassert>
#include <cstdint>
int main() {
    using namespace outrun::vr::dx11::live_game_frame;
    // A real seeded menu Clear permits even an oversized source whose
    // scissor is outside the viewport, without fabricating a D3D11 Draw.
    static_assert(GameNativeScissorClip::excludes_viewport(
        0, 0, 3440, 1440, 3440, 0, 5000, 1440));
    static_assert(!GameNativeScissorClip::excludes_viewport(
        0, 0, 3440, 1440, 3000, 0, 5000, 1440));
    GameNativeFrameBatch frame;
    assert(frame.absorb_empty_source_draw(0, true));
    assert(frame.submitted == 0 && !frame.publishable_full(true, 1));
    assert(frame.accepts_full_seeded(1, true));
    frame.succeeded(false);
    frame.record_source_draw(1);
    assert(frame.absorb_empty_source_draw(2, true));
    assert(frame.absorb_empty_source_draw(3, true));
    assert(frame.submitted == 1 && frame.publishable_full(true, 4));
    assert(!frame.absorb_empty_source_draw(5, true)); // real source gap
    frame.abort();
    assert(!frame.publishable_full(true, 4));
    GameNativeFrameBatch unseeded;
    assert(!unseeded.absorb_empty_source_draw(0, false));
    assert(!unseeded.publishable_full(true, 1));
    // Missing geometry may NOT create a native GPU submission.
    assert(unseeded.submitted == 0u);
    return 0;
}
