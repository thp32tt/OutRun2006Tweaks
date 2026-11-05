#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>

using namespace outrun::vr::dx11::live_game_frame;

constexpr bool menu_vehicle_race_masked_offscreen_continuity() {
    GameNativeClearColor seed{};
    seed.record(3u, 7u, 0xff203040u, true, false, 11u);
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0u, seed.matches(3u, 7u))) return false;
    frame.succeeded(true);
    frame.record_source_draw(0u);
    // A menu RT pass writes only its own auxiliary Z; stencil TEST enabled
    // but write mask zero, while MRT1 points at a bound color-disabled RT.
    if (!GameNativeOffscreenPass::source_has_no_main_writes(
            true, seed.matches(3u, 7u), true,
            GameNativeOffscreenPass::no_main_depth_write(true, true, true),
            GameNativeOffscreenPass::no_main_stencil_write(true, true, 0u),
            GameNativeOffscreenPass::inactive_extra_mrt(true, 0u),
            frame.stopped)) return false;
    seed.note_auxiliary_depth_write();
    if (!frame.absorb_empty_source_draw(1u)) return false;
    // A second game-authored offscreen DrawIndexed reads existing Z and
    // stencil but does not write them or any bound extra color target.
    if (!GameNativeOffscreenPass::source_has_no_main_writes(
            true, seed.matches(3u, 7u), true,
            GameNativeOffscreenPass::no_main_depth_write(true, false),
            GameNativeOffscreenPass::no_main_stencil_write(true, true, 0u),
            GameNativeOffscreenPass::inactive_extra_mrt(true, 0u),
            frame.stopped)) return false;
    if (!frame.absorb_empty_source_draw(2u) ||
        !seed.auxiliaryDepthCleared || !seed.main_depth_still_bound(11u))
        return false;
    // Backbuffer Draw/DrawIndexed continue at the precise source ordinal.
    if (!frame.accepts_full_on_source_target(3u, seed.matches(3u, 7u)))
        return false;
    frame.succeeded(true);
    frame.record_source_draw(3u);
    return frame.submitted == 2u && frame.publishable_full(true, 4u);
}
constexpr bool stencil_mrt_depth_fallback_regressions() {
    using Pass = GameNativeOffscreenPass;
    if (!Pass::no_main_stencil_write(false, false, 0xffffffffu) ||
        !Pass::no_main_stencil_write(true, true, 0u) ||
        Pass::no_main_stencil_write(true, false, 0u) ||
        Pass::no_main_stencil_write(true, true, 1u) ||
        Pass::no_main_stencil_write(true, true, 0xffffffffu))
        return false;
    if (!Pass::inactive_extra_mrt(true, 0u) ||
        Pass::inactive_extra_mrt(false, 0u) ||
        Pass::inactive_extra_mrt(true, 0x8u) ||
        Pass::inactive_extra_mrt(true, 0xffffffffu))
        return false;
    // A main-Z writer, writable stencil, or color-writing extra MRT must
    // cancel optional native publication. Original D3D9 game/input survive.
    for (int bad = 0; bad < 3; ++bad) {
        const bool depth = bad != 0;
        const bool stencil = bad != 1;
        const bool mrt = bad != 2;
        if (Pass::source_has_no_main_writes(
                true, true, true, depth, stencil, mrt, false))
            return false;
    }
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    frame.abort();
    return !frame.absorb_empty_source_draw(1u) &&
           !frame.publishable_full(true, 2u);
}
static_assert(menu_vehicle_race_masked_offscreen_continuity());
static_assert(stencil_mrt_depth_fallback_regressions());
int main() {
    assert(menu_vehicle_race_masked_offscreen_continuity());
    assert(stencil_mrt_depth_fallback_regressions());
}
