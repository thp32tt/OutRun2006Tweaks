#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
int main() {
 GameNativeFrameBatch b{};
 assert(b.accepts_full(0));
 b.succeeded(true); b.record_source_draw(0);
 b.note_full_depth_clear(0.375f);
 assert(b.submitted == 1 && !b.stopped && !b.depthReady);
 assert(b.depth_clear_value(false) == 0.375f && b.accepts_full(1));
 b.consume_depth_clear(); b.succeeded(true); b.record_source_draw(1);
 assert(b.publishable_full(true,2));
 assert(b.depth_clear_value(false) == 1.0f && b.depth_clear_value(true) == 0.0f);
 b.note_full_depth_clear(0.25f); b.abort();
 assert(b.stopped && !b.depthClearPending && !b.publishable_full(true,2));
 b.reset(); assert(!b.stopped && !b.depthClearPending && b.submitted == 0);
 return 0;
}
