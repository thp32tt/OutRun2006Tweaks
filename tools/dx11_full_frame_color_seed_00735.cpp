#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uintptr_t game=0x100u, back=0x200u;
    GameNativeClearColor color{};
    GameNativeFrameBatch batch{};
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back))); // no source Clear
    color.record(game,back,0xff334455u,false);
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back))); // partial
    color.record(game,back,0xff334455u,true);
    assert(batch.accepts_full_seeded(0u,color.matches(game,back))); // real Clear
    assert(!batch.accepts_full_seeded(0u,color.matches(game+1u,back)));
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back+1u)));
    batch.abort(); // pre-first-Draw partial Z or TARGET Clear
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back)));
    batch.reset(); // later successful whole TARGET Clear
    assert(batch.accepts_full_seeded(0u,color.matches(game,back)));
    batch.succeeded(false); batch.record_source_draw(0u);
    // A color-only Clear of an offscreen vehicle/menu RT does not touch
    // the Clear-owned main game backbuffer; the next native indexed or
    // non-indexed Draw must remain eligible on that original RT0.
    assert(color.preserves_offscreen_color_only(game, back, 0x300u, true, batch.stopped));
    assert(batch.accepts_full_on_source_target(1u, color.matches(game, back)));
    assert(!color.preserves_offscreen_color_only(game, back, back, true, batch.stopped));
    assert(!color.preserves_offscreen_color_only(game, back, 0x300u, false, batch.stopped));
    assert(!color.preserves_offscreen_color_only(game+1u, back, 0x300u, true, batch.stopped));
    assert(!color.preserves_offscreen_color_only(game, back+1u, 0x300u, true, batch.stopped));
    assert(!color.preserves_offscreen_color_only(game, back, 0u, true, batch.stopped));
    batch.scene_boundary(); // Main-target or Z/stencil Clear still invalidates.
    assert(!color.preserves_offscreen_color_only(game, back, 0x300u, true, batch.stopped));
    assert(!batch.publishable_full(true, 1u));
    batch.reset();
    assert(batch.accepts_full_seeded(1u,false)); // already seeded, contiguous
    assert(!batch.accepts_full_seeded(2u,true)); // no skipped Draw
    batch.scene_boundary();
    assert(!batch.accepts_full_seeded(1u,true));
    batch.reset(); color.discard();
    assert(!batch.accepts_full_seeded(0u,color.matches(game,back)));
    return 0;
}
