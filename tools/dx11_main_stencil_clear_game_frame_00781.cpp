#include "../src/vr/d3d11/native_game_main_stencil_clear.hpp"
#include "../src/vr/d3d11/native_game_full_color_depth.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
using Gate = GameNativeMainStencilClear;

// A source-authored menu Draw followed by whole-main STENCIL then Z|STENCIL
// Clears and a vehicle/race Draw remains one complete native frame. Both
// original D3D9 Clears/Draws/Present/input remain in the normal call path.
constexpr bool main_stencil_clear_keeps_native_menu_to_race() {
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_seeded(0u, true)) return false;
    frame.succeeded(true);
    frame.record_source_draw(0u);
    if (!Gate::may_ignore(true, true, true, true, !frame.stopped)) return false;
    if (frame.depthClearPending || frame.stopped) return false; // stencil-only
    if (!Gate::may_ignore(true, true, true, true, !frame.stopped) ||
        !GameNativeFullColorDepthClear::can_mirror(true, false, true, 0.25f))
        return false;
    frame.note_full_depth_clear(0.25f); // combined Z+STENCIL
    if (frame.depth_clear_value(false) != 0.25f ||
        !frame.accepts_full_on_source_target(1u, true)) return false;
    frame.consume_depth_clear();
    frame.succeeded(true);
    frame.record_source_draw(1u);
    return frame.publishable_full(true, 2u);
}
constexpr bool unproved_stencil_clear_keeps_original_d3d9() {
    if (Gate::may_ignore(false, true, true, true, true) ||
        Gate::may_ignore(true, false, true, true, true) ||
        Gate::may_ignore(true, true, false, true, true) ||
        Gate::may_ignore(true, true, true, false, true) ||
        Gate::may_ignore(true, true, true, true, false) ||
        GameNativeFullColorDepthClear::can_mirror(true, true, true, 0.25f))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    frame.abort(); // unknown Z/S identity or partial crop must abort native
    return !frame.publishable_full(true, 1u) &&
           !frame.accepts_full_on_source_target(1u, true);
}
static_assert(main_stencil_clear_keeps_native_menu_to_race());
static_assert(unproved_stencil_clear_keeps_original_d3d9());
int main() {
    assert(main_stencil_clear_keeps_native_menu_to_race());
    assert(unproved_stencil_clear_keeps_original_d3d9());
}
