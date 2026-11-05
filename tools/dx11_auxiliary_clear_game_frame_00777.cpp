#include "../src/vr/d3d11/native_game_offscreen_pass.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;

constexpr bool full_game_auxiliary_clear_continuity() {
    GameNativeClearColor seed{};
    seed.record(7, 11, 0xff123456u, true, false, 17);
    if (!seed.matches(7, 11) || !seed.main_depth_still_bound(17)) return false;
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full_on_source_target(0, true)) return false;
    frame.succeeded(true); frame.record_source_draw(0);
    // A separate auxiliary RT and separate Z surface can Clear color/Z
    // between menu, vehicle preview and race game GPU Draws.
    if (!GameNativeOffscreenPass::isolated_auxiliary_clear(
            seed.matches(7, 11), true, true, true, true, frame.stopped)) return false;
    seed.note_auxiliary_depth_clear();
    if (!seed.auxiliaryDepthCleared ||
        !seed.main_depth_still_bound(17) || seed.main_depth_still_bound(19)) return false;
    if (!frame.accepts_full_on_source_target(1, true)) return false;
    frame.succeeded(true); frame.record_source_draw(1);
    if (!frame.publishable_full(true, 2)) return false;
    seed.discard();
    return !seed.mainDepthIdentity && !seed.auxiliaryDepthCleared;
}
constexpr bool auxiliary_clear_fallbacks() {
    auto safe=[](bool seed, bool offscreen, bool mrtFree,
                 bool depth, bool separate, bool stopped) {
        return GameNativeOffscreenPass::isolated_auxiliary_clear(
            seed, offscreen, mrtFree, depth, separate, stopped);
    };
    if (!safe(true, true, true, false, false, false)) return false; // color only
    if (!safe(true, true, true, true, true, false)) return false;   // separate depth
    if (safe(true, false, true, false, true, false) ||
        safe(false, true, true, false, true, false) ||
        safe(true, true, false, false, true, false) || // unknown MRT alias
        safe(true, true, true, true, false, false) || // main Z overwritten
        safe(true, true, true, false, true, true)) return false;
    GameNativeClearColor color{};
    color.record(7, 11, 0, true, false); // no proven main depth surface
    return !color.mainDepthIdentity && !color.main_depth_still_bound(17);
}
static_assert(full_game_auxiliary_clear_continuity());
static_assert(auxiliary_clear_fallbacks());
int main() {
    assert(full_game_auxiliary_clear_continuity());
    assert(auxiliary_clear_fallbacks());
}
