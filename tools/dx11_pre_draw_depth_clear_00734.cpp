#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    constexpr std::uintptr_t game = 0x100u, back = 0x200u;
    GameNativeClearColor color{};
    GameNativeFrameBatch batch{};
    // Real complete TARGET Clear, then separate full Z Clear, then native Draw.
    color.record(game, back, 0xff112233u, true);
    assert(batch.can_seed_pre_draw_depth(color.matches(game, back), true));
    batch.note_full_depth_clear(0.375f);
    assert(batch.depth_clear_value(false) == 0.375f);
    assert(batch.depth_clear_value(true) == 0.375f);
    batch.consume_depth_clear();
    batch.succeeded(true); batch.record_source_draw(0u);
    assert(batch.publishable_full(true, 1u));
    assert(!batch.can_seed_pre_draw_depth(true, true));
    // Post-Draw Z-only Clear uses the existing continuation, not pre-draw.
    batch.reset();
    assert(!batch.can_seed_pre_draw_depth(color.matches(0x101u, back), true));
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, 0x201u), true));
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), false));
    color.record(game, back, 0xff112233u, false);
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), true));
    color.record(game, back, 0xff112233u, true);
    batch.abort();
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), true));
    batch.reset();
    batch.record_source_draw(0u);
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), true));
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), false));
    batch.reset();
    // A successful game-authored empty Draw after a full TARGET Clear is
    // distinct from an unrelated/unaccounted prior Draw. Seed native DSV
    // only for the former, without fabricating a native GPU submission.
    assert(batch.absorb_empty_source_draw(0u, true));
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), true));
    assert(batch.can_seed_pre_draw_depth(color.matches(game, back), false));
    assert(!batch.can_seed_pre_draw_depth(false, false));
    batch.note_full_depth_clear(0.125f);
    assert(batch.first_draw() && batch.depth_clear_value(false) == 0.125f);
    assert(batch.accepts_full_seeded(1u, true));
    batch.succeeded(true); batch.record_source_draw(1u);
    assert(batch.publishable_full(true, 2u));
    batch.reset();
    batch.succeeded(false);
    assert(!batch.can_seed_pre_draw_depth(color.matches(game, back), true));
    return 0;
}
