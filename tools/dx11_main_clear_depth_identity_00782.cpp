#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_clear_coverage.hpp"
#include "../src/vr/d3d11/native_game_main_stencil_clear.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
struct Rect { int x1, y1, x2, y2; };
constexpr Rect clipped[]{{0, 0, 64, 64}};
constexpr Rect whole[]{{0, 0, 1280, 720}};
constexpr bool menu_to_race_partial_stencil_continuity() {
    GameNativeClearColor seed{};
    seed.record(7, 19, 0xff304050u, true, false, 29);
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0, seed.matches(7,19))) return false;
    frame.succeeded(true);
    frame.record_source_draw(0);
    const bool partial = GameNativeClearCoverage::covers_whole(
        1280,720,0,0,1280,720,1,clipped);
    if (partial || !GameNativeMainStencilClear::preserves_clear_coverage(
            false, partial)) return false;
    if (!GameNativeMainStencilClear::may_ignore(
            true, seed.matches(7,19), seed.main_depth_still_bound(29),
            GameNativeMainStencilClear::preserves_clear_coverage(false,partial),
            !frame.stopped)) return false;
    if (frame.depthClearPending || frame.stopped ||
        !frame.accepts_full_on_source_target(1,seed.matches(7,19))) return false;
    frame.succeeded(true); // native vehicle DrawIndexed after partial stencil
    frame.record_source_draw(1);
    const bool full = GameNativeClearCoverage::covers_whole(
        1280,720,0,0,1280,720,1,whole);
    if (!full || !GameNativeMainStencilClear::preserves_clear_coverage(true,full) ||
        !seed.main_depth_still_bound(29)) return false;
    frame.note_full_depth_clear(0.4f);
    if (frame.depth_clear_value(false)!=0.4f ||
        !frame.accepts_full_on_source_target(2,seed.matches(7,19))) return false;
    frame.consume_depth_clear();
    frame.succeeded(true); // native race Draw after whole canonical Z
    frame.record_source_draw(2);
    return frame.publishable_full(true,3);
}
constexpr bool wrong_depth_or_partial_z_falls_back() {
    GameNativeClearColor seed{};
    seed.record(7,19,0xff304050u,true,false,29);
    if (seed.main_depth_still_bound(99) || seed.main_depth_still_bound(0) ||
        !GameNativeMainStencilClear::preserves_clear_coverage(false,false) ||
        GameNativeMainStencilClear::preserves_clear_coverage(true,false))
        return false;
    GameNativeFrameBatch frame{};
    frame.succeeded(true);
    frame.record_source_draw(0);
    frame.scene_boundary(); // original D3D9 Clear still executes
    return !frame.publishable_full(true,1) &&
           !frame.accepts_full_on_source_target(1,true);
}
static_assert(menu_to_race_partial_stencil_continuity());
static_assert(wrong_depth_or_partial_z_falls_back());
int main(){
    assert(menu_to_race_partial_stencil_continuity());
    assert(wrong_depth_or_partial_z_falls_back());
}
