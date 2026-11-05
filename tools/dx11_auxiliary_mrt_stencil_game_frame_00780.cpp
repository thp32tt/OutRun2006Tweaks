#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
using Pass = GameNativeOffscreenPass;

// One actual game-frame source stream: main Draw, writable auxiliary MRT +
// stencil DrawIndexed, auxiliary TARGET/Z/STENCIL Clear, then main race Draw.
constexpr bool main_menu_car_race_frame_over_auxiliary_outputs() {
    GameNativeClearColor main{};
    main.record(4u, 10u, 0xff203040u, true, false, 11u);
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0u, main.matches(4u, 10u)))
        return false;
    frame.succeeded(true);
    frame.record_source_draw(0u);
    const bool independentMrt1 = Pass::distinct_auxiliary_mrt(12u, 10u);
    const bool independentZs = !main.main_depth_still_bound(13u);
    if (!Pass::source_has_no_main_writes(
            true, main.matches(4u, 10u), true,
            Pass::no_main_depth_write(true, true, independentZs),
            Pass::no_main_stencil_write(true, true, 0xffu) ||
                Pass::isolated_auxiliary_stencil_write(
                    true, true, 0xffu, independentZs),
            independentMrt1, frame.stopped))
        return false;
    main.note_auxiliary_depth_write();
    if (!frame.absorb_empty_source_draw(1u) || !main.auxiliaryDepthCleared)
        return false;
    // Clear ignores per-MRT color masks; each bound auxiliary target is
    // distinct from main, and the Z/stencil surface is independent.
    if (!Pass::isolated_auxiliary_clear(true, true, independentMrt1,
                                        true, independentZs, frame.stopped))
        return false;
    main.note_auxiliary_depth_clear();
    if (!frame.accepts_full_on_source_target(2u, main.matches(4u, 10u)) ||
        !main.main_depth_still_bound(11u))
        return false;
    frame.succeeded(true);
    frame.record_source_draw(2u);
    return frame.submitted == 2u && frame.publishable_full(true, 3u);
}
constexpr bool unsafe_main_alias_and_unknown_state_stay_d3d9() {
    if (!Pass::distinct_auxiliary_mrt(12u, 10u) ||
        Pass::distinct_auxiliary_mrt(10u, 10u) ||
        Pass::distinct_auxiliary_mrt(0u, 10u) ||
        Pass::distinct_auxiliary_mrt(12u, 0u))
        return false;
    // A zero color mask may protect a Draw but never a TARGET Clear.
    if (!Pass::inactive_extra_mrt(true, 0u) ||
        Pass::inactive_extra_mrt(true, 0x0fu))
        return false;
    if (!Pass::no_main_stencil_write(true, true, 0u) ||
        Pass::no_main_stencil_write(true, true, 0xffu) ||
        !Pass::isolated_auxiliary_stencil_write(true, true, 0xffu, true) ||
        Pass::isolated_auxiliary_stencil_write(true, true, 0xffu, false) ||
        Pass::isolated_auxiliary_stencil_write(true, false, 0xffu, true) ||
        Pass::isolated_auxiliary_stencil_write(false, true, 0xffu, true))
        return false;
    if (Pass::source_has_no_main_writes(
            true, true, true, true,
            Pass::no_main_stencil_write(true, true, 0xffu) ||
                Pass::isolated_auxiliary_stencil_write(true, true, 0xffu, false),
            Pass::distinct_auxiliary_mrt(10u, 10u), false))
        return false;
    if (Pass::isolated_auxiliary_clear(
            true, true, Pass::distinct_auxiliary_mrt(10u, 10u),
            true, true, false))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0u);
    frame.abort();
    return !frame.absorb_empty_source_draw(1u) &&
        !frame.publishable_full(true, 2u);
}

// Whole live main Draw -> auxiliary Z/STENCIL Clear with main RT0 bound ->
// main Draw -> same-Present publication. No native color/Z writes are lost.
constexpr bool main_rt_auxiliary_z_clear_continuity() {
    GameNativeClearColor main{};
    main.record(4u, 10u, 0xff203040u, true, false, 11u);
    GameNativeFrameBatch batch{};
    if (!batch.accepts_full_on_source_target(0u, main.matches(4u, 10u))) return false;
    batch.succeeded(true); batch.record_source_draw(0u);
    const bool auxiliaryZ = !main.main_depth_still_bound(13u);
    if (!Pass::isolated_auxiliary_clear(
            main.matches(4u, 10u), false, true, true,
            auxiliaryZ, batch.stopped, false)) return false;
    main.note_auxiliary_depth_clear();
    if (!main.auxiliaryDepthCleared || !main.main_depth_still_bound(11u)) return false;
    if (!batch.accepts_full_on_source_target(1u, main.matches(4u, 10u))) return false;
    batch.succeeded(true); batch.record_source_draw(1u);
    return batch.publishable_full(true, 2u);
}
constexpr bool auxiliary_z_clear_fail_closed() {
    // Main color TARGET|Z is NOT isolated, even if Z is auxiliary.
    if (Pass::isolated_auxiliary_clear(true,false,true,true,true,false,true))
        return false;
    // Main/unknown depth, missing game color seed or stopped batch.
    if (Pass::isolated_auxiliary_clear(true,false,true,true,false,false,false) ||
        Pass::isolated_auxiliary_clear(false,false,true,true,true,false,false) ||
        Pass::isolated_auxiliary_clear(true,false,true,true,true,true,false))
        return false;
    // An offscreen TARGET Clear with an active/unknown MRT cannot be skipped.
    if (Pass::isolated_auxiliary_clear(true,true,false,false,false,false,true))
        return false;
    // An isolated TARGET-only Clear does not write depth, even if main Z bound.
    return Pass::isolated_auxiliary_clear(true,true,true,false,false,false,true);
}
static_assert(main_rt_auxiliary_z_clear_continuity());
static_assert(auxiliary_z_clear_fail_closed());
static_assert(main_menu_car_race_frame_over_auxiliary_outputs());
static_assert(unsafe_main_alias_and_unknown_state_stay_d3d9());
int main() {
    assert(main_rt_auxiliary_z_clear_continuity());
    assert(auxiliary_z_clear_fail_closed());
    assert(main_menu_car_race_frame_over_auxiliary_outputs());
    assert(unsafe_main_alias_and_unknown_state_stay_d3d9());
}
