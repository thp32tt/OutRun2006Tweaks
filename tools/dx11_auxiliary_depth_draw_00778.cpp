#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>

using namespace outrun::vr::dx11::live_game_frame;
constexpr bool menu_vehicle_race_offscreen_depth_draws() {
    GameNativeClearColor main{};
    main.record(7u, 11u, 0xff234567u, true, false, 17u);
    if (!main.matches(7u, 11u) || !main.main_depth_still_bound(17u)) return false;
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0u, true)) return false;
    frame.succeeded(true); frame.record_source_draw(0u);
    // Actual offscreen RT0 with a different Z surface is permitted even
    // when the game's original DrawIndexed writes auxiliary depth.
    const bool otherDepth = !main.main_depth_still_bound(19u);
    if (!GameNativeOffscreenPass::source_has_no_main_writes(
            true, true, true,
            GameNativeOffscreenPass::no_main_depth_write(true, true, otherDepth),
            true, true, frame.stopped)) return false;
    main.note_auxiliary_depth_write();
    if (!main.auxiliaryDepthCleared || !main.main_depth_still_bound(17u) ||
        main.main_depth_still_bound(19u)) return false;
    if (!frame.absorb_empty_source_draw(1u)) return false;
    if (!frame.accepts_full_on_source_target(2u, true)) return false;
    frame.succeeded(true); frame.record_source_draw(2u);
    const bool eligible = frame.publishable_full(true, 3u) &&
        main.main_depth_still_bound(17u) && frame.submitted == 2u;
    main.discard();
    return eligible && !main.auxiliaryDepthCleared && !main.mainDepthIdentity;
}
constexpr bool unsafe_depth_and_mrt_keep_original_fallback() {
    GameNativeClearColor main{};
    main.record(7u, 11u, 0xff000000u, true, false, 17u);
    if (GameNativeOffscreenPass::no_main_depth_write(true, true) ||
        GameNativeOffscreenPass::no_main_depth_write(true, true,
            !main.main_depth_still_bound(17u))) return false;
    if (!GameNativeOffscreenPass::no_main_depth_write(true, false) ||
        !GameNativeOffscreenPass::no_main_depth_write(false, true)) return false;
    const auto safe=[](bool seed, bool offscreen, bool depth, bool stencil,
                       bool mrt, bool stopped) {
        return GameNativeOffscreenPass::source_has_no_main_writes(
            true, seed, offscreen, depth, stencil, mrt, stopped);
    };
    if (safe(true, true, false, true, true, false) ||
        safe(false, true, true, true, true, false) ||
        safe(true, false, true, true, true, false) ||
        safe(true, true, true, false, true, false) ||
        safe(true, true, true, true, false, false) ||
        safe(true, true, true, true, true, true)) return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true); frame.record_source_draw(0u);
    frame.abort();
    return !frame.absorb_empty_source_draw(1u) &&
        !frame.publishable_full(true, 2u);
}
static_assert(menu_vehicle_race_offscreen_depth_draws());
static_assert(unsafe_depth_and_mrt_keep_original_fallback());
int main() {
    assert(menu_vehicle_race_offscreen_depth_draws());
    assert(unsafe_depth_and_mrt_keep_original_fallback());
}
