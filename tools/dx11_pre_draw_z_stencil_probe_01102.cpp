// 01102 original game clipped Z|STENCIL before first native Draw.
#include "../src/vr/d3d11/native_game_pre_draw_depth.hpp"
#include "../src/vr/d3d11/native_game_main_stencil_clear.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
struct Rect { long x1,y1,x2,y2; };
int main() {
    GameNativeFrameBatch batch{};
    batch.note_full_depth_clear(1.f);
    assert(batch.can_seed_pre_draw_depth(true,true));
    assert(GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,true,true,true));
    // This original Draw wrote no pixels; only its source ordinal advances.
    assert(batch.absorb_empty_source_draw(0u,true));
    assert(batch.can_seed_pre_draw_depth(true,false));
    assert(!batch.can_seed_pre_draw_depth(false,false));
    GameNativePreDrawDepth z{};
    constexpr std::uintptr_t device=7,rt=11,depthOwner=13;
    constexpr std::uint32_t W=10,H=8;
    const Rect rects[]={{-2,2,4,6},{8,0,14,4}};
    assert(z.record(device,rt,depthOwner,W,H,0,0,W,H,2,rects,0.4f));
    assert(z.count==2 && z.tiles[0].left==0 && z.tiles[1].right==W);
    const Rect overlay[]={{3,3,7,8}};
    assert(z.record(device,rt,depthOwner,W,H,0,0,W,H,1,overlay,0.2f));
    std::array<float,W*H> pixels{};
    pixels.fill(batch.depth_clear_value(false));
    for(std::uint32_t i=0;i<z.count;++i) {
        const auto& r=z.tiles[i];
        for(auto y=r.top;y<r.bottom;++y)
            for(auto x=r.left;x<r.right;++x)
                pixels[std::size_t(y)*W+std::size_t(x)]=r.z;
    }
    assert(pixels[2u*W+0u]==0.4f);
    assert(pixels[2u*W+9u]==0.4f);
    assert(pixels[4u*W+5u]==0.2f);
    assert(pixels[4u*W+2u]==0.4f);
    assert(pixels[0]==1.f);
    assert(z.replay_ready(device,rt,depthOwner,W,H));
    assert(!z.replay_ready(device,rt,depthOwner+1,W,H));
    const Rect invalid[]={{3,3,4,5},{5,6,5,7}};
    const auto originalCount=z.count;
    assert(!z.record(device,rt,depthOwner,W,H,0,0,W,H,2,invalid,.5f));
    assert(!z.record(device,rt,depthOwner+1,W,H,0,0,W,H,1,overlay,.6f));
    assert(!z.record(device,rt,depthOwner,W,H,0,0,W,H,1,overlay,
                     std::numeric_limits<float>::quiet_NaN()));
    assert(z.count==originalCount);
    assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,false,true,true));
    assert(!GameNativeMainStencilClear::may_ignore_pre_draw(
        true,true,true,false,true));
    batch.consume_depth_clear();
    // The batch helper validates Draw ordinals and source continuity only.
    // The live hook additionally requires the authentic pending full Z seed.
    assert(!batch.depthClearPending);
    assert(!(batch.depthClearPending &&
             batch.can_seed_pre_draw_depth(true,false)));
}
