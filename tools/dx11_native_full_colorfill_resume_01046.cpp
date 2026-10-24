#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_color_fill.hpp"
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
using outrun::vr::dx11::native_game_color_fill_retires_draw_batch;
int main() {
    // Real game's first Draw then full ColorFill then another game Draw.
    GameNativeFrameBatch b{};
    assert(b.accepts_full_on_source_target(0, true));
    b.record_source_draw(0); b.succeeded(false);
    assert(b.publishable_full(true, 1));
    assert(native_game_color_fill_retires_draw_batch(true, b.submitted != 0u));
    assert(b.restart_after_full_color_fill(1));
    assert(!b.publishable_full(true, 1)); // Old native GPU Draw is retired.
    assert(!b.accepts_full_on_source_target(0, true));
    assert(b.accepts_full_on_source_target(1, true));
    assert(!b.accepts_full_on_source_target(2, true)); // Cannot skip real Draw.
    assert(b.accepts_depth(false, false));
    assert(!b.accepts_depth(true, false)); // ColorFill did not reset game Z.
    b.record_source_draw(1); b.succeeded(false);
    assert(b.publishable_full(true, 2));
    assert(!b.publishable_full(true, 3));
    assert(!b.restart_after_full_color_fill(2)); // Do not repeat unproven Z epoch.
    b.abort();
    assert(!b.publishable_full(true, 2));
    // Source no-op after recovery consumes its absolute original ordinal.
    GameNativeFrameBatch empty{};
    empty.record_source_draw(0); empty.succeeded(false);
    assert(empty.restart_after_full_color_fill(1));
    assert(empty.absorb_empty_source_draw(1, true));
    assert(empty.accepts_full_on_source_target(2, true));
    empty.record_source_draw(2); empty.succeeded(false);
    assert(empty.publishable_full(true, 3));
    // Any previously poisoned, partial, unproven or depth-writing scene fails closed.
    GameNativeFrameBatch poisoned{};
    poisoned.record_source_draw(0); poisoned.succeeded(false);
    poisoned.abort();
    assert(!poisoned.restart_after_full_color_fill(1));
    GameNativeFrameBatch gap{};
    gap.record_source_draw(0); gap.succeeded(false);
    assert(!gap.restart_after_full_color_fill(2));
    GameNativeFrameBatch depth{};
    depth.record_source_draw(0); depth.succeeded(true);
    assert(!depth.restart_after_full_color_fill(1));
    GameNativeFrameBatch depthPending{};
    depthPending.record_source_draw(0); depthPending.succeeded(false);
    depthPending.note_full_depth_clear(0.4f);
    assert(!depthPending.restart_after_full_color_fill(1));
    GameNativeFrameBatch neverDraw{};
    assert(!neverDraw.restart_after_full_color_fill(0));
    // Legacy non-epoch baseline remains unchanged.
    GameNativeFrameBatch normal{};
    normal.record_source_draw(0); normal.succeeded(true);
    assert(normal.accepts_depth(true, false));
    assert(normal.publishable_full(true, 1));
}
