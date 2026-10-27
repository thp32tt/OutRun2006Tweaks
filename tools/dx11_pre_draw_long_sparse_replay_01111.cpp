// 01111: authentic D3D9 pre-first-Draw TARGET|Z sparse menu/car/race
// regions are replayed as a single complete ordered native RTV/D32 epoch.
// Pixels in gaps must remain untouched; fail-closed source owner and overflow.
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_replay.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
constexpr std::uint32_t W=384u,H=5u;
using Colors=std::array<std::uint32_t,W*H>;
using Depths=std::array<float,W*H>;
void paint(Colors& frame,const Rect& r,std::uint32_t color){
    for(long y=r.y1;y<r.y2;++y)
        for(long x=r.x1;x<r.x2;++x)
            frame[std::size_t(y)*W+std::size_t(x)]=color;
}
void paint(Depths& frame,const Rect& r,float z){
    for(long y=r.y1;y<r.y2;++y)
        for(long x=r.x1;x<r.x2;++x)
            frame[std::size_t(y)*W+std::size_t(x)]=z;
}
std::uint32_t pack(const GameNativePreDrawTile& t){
    const auto byte=[](float f){return std::uint32_t(f*255.f+.5f);};
    return (byte(t.rgba[3])<<24u)|(byte(t.rgba[0])<<16u)|
           (byte(t.rgba[1])<<8u)|byte(t.rgba[2]);
}
Colors replayColor(const GameNativePreDrawFills& color,bool clearView) {
    Colors gpu{};gpu.fill(0xff000000u);
    auto writer=[&](const GameNativePreDrawTile& t) noexcept {
        paint(gpu,{long(t.left),long(t.top),long(t.right),long(t.bottom)},pack(t));
        return true;
    };
    assert(game_native_replay_pre_draw_fills(
        color,7,11,W,H,false,clearView,writer,writer));
    return gpu;
}
Depths replayDepth(const GameNativePreDrawDepth& depth,
                   std::uint32_t& batches,std::uint32_t& largest) {
    Depths gpu{};gpu.fill(1.f);
    batches=largest=0u;
    assert(depth.replay_batched(
        7,11,13,W,H,
        [&](const GameNativePreDrawDepth::Tile* tiles,
            std::uint32_t count,float z) noexcept {
            assert(count>0u&&count<=GameNativePreDrawDepth::kGpuChunkCapacity);
            ++batches;if(count>largest)largest=count;
            for(std::uint32_t i=0u;i<count;++i)
                paint(gpu,{long(tiles[i].left),long(tiles[i].top),
                           long(tiles[i].right),long(tiles[i].bottom)},z);
            return true;
        }));
    return gpu;
}
}
int main(){
    static_assert(GameNativePreDrawFills::kCapacity==128u);
    static_assert(GameNativePreDrawDepth::kCapacity==128u);
    static_assert(GameNativePreDrawDepth::kGpuChunkCapacity==32u);
    std::array<Rect,128> rects{};
    for(std::uint32_t i=0u;i<rects.size();++i)
        rects[i]={long(i*3u),1,long(i*3u+2u),3};
    GameNativePreDrawFills color{};
    GameNativePreDrawDepth depth{};
    Colors expectedColor{};expectedColor.fill(0xff000000u);
    Depths expectedDepth{};expectedDepth.fill(1.f);
    // Interleaved authentic separate game Clears cannot be reordered across
    // different color/Z writes even though every source remains contiguous.
    for(std::uint32_t i=0u;i<rects.size();++i){
        const std::uint32_t argb=0xff100000u+i;
        const float z=(i&1u)? .25f : .75f;
        assert(GameNativePreDrawCombinedClear::record(
            color,depth,7,11,13,W,H,0,0,W,H,1,&rects[i],argb,z));
        paint(expectedColor,rects[i],argb);
        paint(expectedDepth,rects[i],z);
    }
    assert(color.count==128u&&depth.count==128u);
    assert(replayColor(color,true)==expectedColor);
    assert(replayColor(color,false)==expectedColor);
    std::uint32_t batches=0,largest=0;
    assert(replayDepth(depth,batches,largest)==expectedDepth);
    assert(batches==128u&&largest==1u); // interleaved Z may not group.
    // Foreign RT/depth, invalid extent and malformed source must refuse
    // BEFORE writing any native output, keeping original DX9Ex authoritative.
    std::uint32_t calls=0;
    auto accept=[&](const GameNativePreDrawDepth::Tile*,
                    std::uint32_t,float) noexcept {++calls;return true;};
    assert(!depth.replay_batched(7,11,14,W,H,accept));
    assert(!depth.replay_batched(7,12,13,W,H,accept));
    assert(!depth.replay_batched(7,11,13,W-1u,H,accept));
    assert(calls==0u);
    const auto oldColor=color.count,oldDepth=depth.count;
    const Rect extra{0,4,1,5};
    assert(!GameNativePreDrawCombinedClear::record(
        color,depth,7,11,13,W,H,0,0,W,H,1,&extra,0xff007711u,.4f));
    assert(color.count==oldColor&&depth.count==oldDepth);
    const Rect malformed[]={{0,0,1,2},{10,3,2,4}};
    assert(!GameNativePreDrawCombinedClear::record(
        color,depth,7,11,13,W,H,0,0,W,H,2,malformed,0xff007711u,.4f));
    assert(!GameNativePreDrawCombinedClear::record(
        color,depth,7,11,13,W,H,0,0,W,H,129u,rects.data(),
        0xff007711u,.4f));
    assert(replayColor(color,true)==expectedColor);
    assert(replayDepth(depth,batches,largest)==expectedDepth);
    // One authentic 128-D3DRECT TARGET|Z call must also replay intact.
    color.discard();depth.discard();
    expectedColor.fill(0xff000000u);
    expectedDepth.fill(1.f);
    assert(GameNativePreDrawCombinedClear::record(
        color,depth,7,11,13,W,H,0,0,W,H,128u,rects.data(),
        0xffabcdefu,.35f));
    for(const Rect& r:rects){
        paint(expectedColor,r,0xffabcdefu);
        paint(expectedDepth,r,.35f);
    }
    assert(color.count==128u&&depth.count==128u);
    assert(replayColor(color,true)==expectedColor);
    assert(replayDepth(depth,batches,largest)==expectedDepth);
    assert(batches==4u&&largest==32u);
    // Emission failure may abort this native candidate; the original source
    // ledgers remain intact for an untouched D3D9 frame.
    assert(!depth.replay_batched(
        7,11,13,W,H,
        [](const GameNativePreDrawDepth::Tile*,std::uint32_t,float) noexcept {
            return false;
        }));
    assert(replayDepth(depth,batches,largest)==expectedDepth);
}
