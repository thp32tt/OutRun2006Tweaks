// 01056: persist genuine native full-frame source through multiple real
// D3D9 post-Draw GPU tile readbacks while charging any fallback FULL bytes.
#include "../src/vr/d3d11/native_game_surface_replay_budget.hpp"
#include "../src/vr/d3d11/native_game_surface_tile_plan.hpp"
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceReplayBudget;
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceTilePlan;
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceCopyRegion;
int main() {
    using B=GameNativeSurfaceReplayBudget;
    constexpr auto tile=GameNativeSurfaceCopyRegion::destination(
        30,40,94,104,3440,1440);
    constexpr auto full=GameNativeSurfaceCopyRegion::destination(
        0,0,3440,1440,3440,1440);
    static_assert(GameNativeSurfaceTilePlan::eligible(tile,3440,1440));
    static_assert(!GameNativeSurfaceTilePlan::eligible(full,3440,1440));
    constexpr auto tileBytes=B::full_readback_bytes(tile.width(),tile.height());
    constexpr auto fullBytes=B::full_readback_bytes(3440,1440);
    static_assert(tileBytes==16384u && fullBytes==19814400u);
    B b{};
    b.note_success(3440,1440); // cold/Reset first native Draw seed
    for(unsigned i=0;i<30u;++i) {
        assert(b.admits_bytes(tileBytes));
        b.note_success_bytes(tileBytes);
    }
    assert(b.operations==31u && b.bytes==fullBytes+30u*tileBytes);
    for(unsigned i=0;i<11u;++i) {
        assert(b.admits(3440,1440));
        b.note_success(3440,1440); // driver tile failure: full RT readback
    }
    assert(!b.admits(3440,1440) && b.admits_bytes(tileBytes));
    const auto stable=b.bytes, count=b.operations;
    b.note_success_bytes(fullBytes); // denied fallback MUST be side-effect free
    assert(b.bytes==stable && b.operations==count);
    b.note_success_bytes(tileBytes);
    assert(b.bytes==stable+tileBytes && b.operations==count+1u);
    assert(!b.admits_bytes(0u) && !b.admits_bytes(B::kMaxBytes+1u));
    b.reset();
    assert(b.bytes==0u && b.operations==0u && b.admits(3440,1440));
    B runaway{};
    for(unsigned i=0;i<B::kMaxOperations;++i) {
        assert(runaway.admits_bytes(tileBytes));
        runaway.note_success_bytes(tileBytes);
    }
    assert(!runaway.admits_bytes(tileBytes)); // original operation cap preserved
}
