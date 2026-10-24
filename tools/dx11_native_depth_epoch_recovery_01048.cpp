#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_full_color_depth.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uintptr_t owner = 0x1230u, color = 0x2340u, depth = 0x3450u;
    GameNativeClearColor seed{};
    seed.record(owner,color,0xff112233u,true,false,depth);
    assert(seed.matches(owner,color));
    assert(seed.main_depth_still_bound(depth));
    assert(!seed.main_depth_still_bound(depth + 1u));
    assert(GameNativeFullColorDepthClear::can_mirror(true,false,true,0.3f));
    assert(!GameNativeFullColorDepthClear::can_mirror(true,false,true,1.1f));

    // A real menu -> car -> race frame has already written GPU depth.
    GameNativeFrameBatch b{};
    assert(b.accepts_full_on_source_target(0u,seed.matches(owner,color)));
    b.record_source_draw(0u); b.succeeded(true);
    b.record_source_draw(1u); b.succeeded(true);
    assert(b.publishable_full(true,2u));
    assert(!b.restart_after_full_color_fill(2u)); // historical contract
    assert(b.defer_full_color_fill_until_depth_clear(2u));
    assert(b.awaitingColorFillDepthReset && b.colorFillEpoch);
    assert(!b.publishable_full(true,2u)); // retire erased native color
    assert(!b.accepts_full_on_source_target(2u,true)); // no draw before Z
    assert(!b.absorb_empty_source_draw(2u,true));
    assert(!b.resume_after_game_full_depth_clear(1u,0.6f));
    assert(!b.resume_after_game_full_depth_clear(2u,1.1f));
    assert(!b.resume_after_game_full_depth_clear(2u,-0.1f));
    assert(b.awaitingColorFillDepthReset);
    // The observer verifies real game-owned full Z coverage and identity.
    assert(b.resume_after_game_full_depth_clear(2u,0.6f));
    assert(!b.awaitingColorFillDepthReset && !b.colorFillEpoch);
    assert(b.depthClearPending && b.depth_clear_value(false)==0.6f);
    assert(!b.resume_after_game_full_depth_clear(2u,0.2f));
    assert(!b.publishable_full(true,2u));
    assert(!b.accepts_full_on_source_target(1u,true));
    assert(b.accepts_full_on_source_target(2u,true));
    assert(b.accepts_depth(true,false));
    b.record_source_draw(2u); b.succeeded(true);
    b.consume_depth_clear();
    assert(b.publishable_full(true,3u));
    // Same Present: a second genuine color overwrite and game full Z Clear
    // must retire even the previously recovered GPU epoch.
    assert(b.defer_full_color_fill_until_depth_clear(3u));
    assert(!b.publishable_full(true,3u));
    assert(b.resume_after_game_full_depth_clear(3u,0.2f));
    b.record_source_draw(3u); b.succeeded(true);
    assert(b.publishable_full(true,4u));
    assert(!b.publishable_full(true,5u));

    GameNativeFrameBatch gap{};
    gap.record_source_draw(0u); gap.succeeded(true);
    assert(!gap.defer_full_color_fill_until_depth_clear(2u));
    assert(gap.publishable_full(true,1u));
    GameNativeFrameBatch poisoned{};
    poisoned.record_source_draw(0u); poisoned.succeeded(true);
    poisoned.abort();
    assert(!poisoned.defer_full_color_fill_until_depth_clear(1u));
    GameNativeFrameBatch empty{};
    empty.record_source_draw(0u); empty.succeeded(false);
    assert(!empty.defer_full_color_fill_until_depth_clear(1u));
    GameNativeFrameBatch pendingZ{};
    pendingZ.record_source_draw(0u); pendingZ.succeeded(false);
    pendingZ.note_full_depth_clear(0.75f);
    assert(!pendingZ.restart_after_full_color_fill(1u));
    assert(pendingZ.defer_full_color_fill_until_depth_clear(1u));
    pendingZ.abort();
    assert(!pendingZ.resume_after_game_full_depth_clear(1u,0.8f));
    pendingZ.reset();
    assert(!pendingZ.awaitingColorFillDepthReset);
    assert(!pendingZ.resume_after_game_full_depth_clear(0u,0.8f));
    // Normal Z Draws and color-only chained transitions stay unaffected.
    GameNativeFrameBatch plain{};
    plain.record_source_draw(0u); plain.succeeded(false);
    assert(plain.restart_after_full_color_fill(1u));
    assert(plain.accepts_full_on_source_target(1u,true));
    assert(!plain.accepts_depth(true,false));
    assert(!plain.awaitingColorFillDepthReset);
    return 0;
}
