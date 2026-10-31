// 01057: Source-level game CPU/GDI tile start -> completed native GPU tile
// admission. Readback failure still needs a second, FULL-source admission.
#include "../src/vr/d3d11/native_game_cpu_tile_admission.hpp"
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeCpuTileAdmission;
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceCopyRegion;
using outrun::vr::dx11::live_game_frame::GameNativeSurfaceReplayBudget;
int main() {
    using P=GameNativeCpuTileAdmission;
    using B=GameNativeSurfaceReplayBudget;
    constexpr auto tile=GameNativeSurfaceCopyRegion::destination(
        123,31,187,95,3440,1440);
    constexpr auto full=GameNativeSurfaceCopyRegion::destination(
        0,0,3440,1440,3440,1440);
    constexpr auto invalid=GameNativeSurfaceCopyRegion::destination(
        -1,0,64,64,3440,1440);
    constexpr auto tileCost=P::planned_bytes(tile,3440,1440,false);
    constexpr auto fullCost=P::planned_bytes(tile,3440,1440,true);
    static_assert(tileCost==64u*64u*4u);
    static_assert(fullCost==3440u*1440u*4u);
    static_assert(P::planned_bytes(full,3440,1440,false)==fullCost);
    static_assert(P::planned_bytes(invalid,3440,1440,false)==0u);
    static_assert(P::planned_bytes(tile,1920,1080,false)==tileCost);
    static_assert(P::planned_bytes(tile,100,60,false)==0u);
    B budget{};
    for(unsigned i=0u;i<13u;++i) {
        assert(budget.admits_bytes(fullCost));
        budget.note_success_bytes(fullCost);
    }
    assert(!budget.admits_bytes(fullCost)); // full cold/GetDC now rejected
    assert(budget.admits_bytes(tileCost)); // original post-Draw LockRect can continue
    for(unsigned i=0u;i<16u;++i) {
        assert(budget.admits_bytes(tileCost));
        budget.note_success_bytes(tileCost); // game GPU tile capture + DX11 copy
    }
    assert(budget.operations==29u);
    // Driver failed GPU crop: full-source readback MUST be denied before
    // attempting GetRenderTargetData; original D3D9 result is untouched.
    const auto stable=budget.bytes;
    const auto operations=budget.operations;
    assert(!budget.admits_bytes(fullCost));
    budget.note_success_bytes(fullCost);
    assert(budget.bytes==stable && budget.operations==operations);
    budget.reset(); // game Reset / new native frame
    assert(budget.admits_bytes(fullCost));
    budget.note_success_bytes(fullCost); // cold menu/vehicle source must be full
    assert(budget.bytes==fullCost && budget.operations==1u);
}
