// Native 01113 source-covering regression: authentic D3D9 copy first-Draw.
#include "../src/vr/d3d11/native_game_full_copy_seed.hpp"
#include "../src/vr/d3d11/native_game_clear_color.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_surface.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    auto admits=[](std::array<bool,7> p) {
        return native_game_full_surface_copy_can_seed(
            p[0],p[1],p[2],p[3],p[4],p[5],p[6]);
    };
    std::array<bool,7> admission{true,true,true,true,true,true,true};
    assert(admits(admission));
    for (std::size_t i=0;i<admission.size();++i) {
        auto denied=admission; denied[i]=false; assert(!admits(denied));
    }
    // A real menu can begin with StretchRect/UpdateSurface without a
    // D3D9 TARGET Clear: previously this case was always rejected before
    // the whole-copy bootstrap predicate was reached.
    assert(native_game_full_surface_copy_can_continue(false,false,true));
    assert(native_game_full_surface_copy_can_continue(true,true,false));
    assert(!native_game_full_surface_copy_can_continue(false,false,false));
    assert(!native_game_full_surface_copy_can_continue(true,false,false));
    assert(!native_game_full_surface_copy_can_continue(false,true,false));
    assert(!native_game_full_surface_copy_can_continue(false,false,false));
    // Even a previously seeded Clear cannot move to a different source.
    assert(!native_game_full_surface_copy_can_continue(false,true,false));
    GameNativeClearColor color;
    color.record(0x11u,0x22u,0u,true,true,0x33u);
    color.copySnapshotRequired=true;
    GameNativePreDrawSurface snapshot;
    assert(color.matches(0x11u,0x22u));
    assert(color.copySnapshotRequired && !snapshot.active());
    std::vector<std::uint8_t> source(3u*2u*4u,0x7bu);
    assert(snapshot.record_consuming(0x11u,0x22u,3u,2u,21u,source));
    assert(snapshot.matches(0x11u,0x22u,3u,2u,21u));
    assert(!snapshot.matches(0x12u,0x22u,3u,2u,21u));
    assert(!snapshot.matches(0x11u,0x22u,3u,2u,22u));
    assert(!snapshot.matches(0x11u,0x22u,4u,2u,21u));
    snapshot.discard();
    assert(!snapshot.active() && color.copySnapshotRequired);
    color.discard();
    assert(!color.copySnapshotRequired && !color.valid);
}
