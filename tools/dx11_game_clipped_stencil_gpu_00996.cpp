#include "../src/vr/d3d11/native_game_main_stencil_clear.hpp"
#include "../src/vr/d3d11/native_game_source_mutation.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeMainStencilClear;
using outrun::vr::dx11::live_game_frame::GameNativeSourceMutation;
constexpr bool valid_clipped_main_clear() {
    using Gate = GameNativeMainStencilClear;
    GameNativeSourceMutation::TargetClearRect bounds{};
    const auto kind = GameNativeSourceMutation::classify_target_clear_rect(
        5, 6, 100, 90, 10, 12, 70, 50, 1280, 720, bounds);
    if (kind != GameNativeSourceMutation::TargetClearClip::Pixels ||
        bounds.left != 10 || bounds.top != 12 ||
        bounds.right != 80 || bounds.bottom != 62) return false;
    // Canonical main TARGET|STENCIL, Z|STENCIL, TARGET|Z|STENCIL
    // are stencil-neutral only for a bounded live native frame with D32.
    if (!Gate::may_ignore_cropped(true,true,true,true,true,true)) return false;
    if (!GameNativeSourceMutation::mirrors_partial_target_clear(
        true,true,true,true,true,true,true)) return false;
    if (!GameNativeSourceMutation::mirrors_partial_depth_clear(
        true,true,true,true,true,true)) return false;
    for (int missing = 0; missing < 6; ++missing) {
        bool guards[6] = {true,true,true,true,true,true};
        guards[missing] = false;
        if (Gate::may_ignore_cropped(
            guards[0], guards[1], guards[2], guards[3],
            guards[4], guards[5])) return false;
    }
    if (Gate::may_ignore_cropped(true,true,true,true,false,true))
        return false; // invalid/disjoint clips are not a license to clear
    if (GameNativeSourceMutation::classify_target_clear_rect(
        80, 60, 90, 70, 10, 12, 70, 50, 1280, 720, bounds)
        != GameNativeSourceMutation::TargetClearClip::Empty) return false;
    // Legacy whole-clear policy still rejects cropped depth coverage.
    return !Gate::may_ignore(true,true,true,false,true);
}
static_assert(valid_clipped_main_clear(), "source depth/stencil owner regression");
int main() { assert(valid_clipped_main_clear()); }
