// Authentic D3D9 partial Z and TARGET|Z / Z|STENCIL source chronology:
// many source writes compact to 32 exact GPU tiles without inventing pixels.
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
constexpr unsigned W=48u,H=24u;
using Depth=std::array<float,W*H>;
using Color=std::array<std::uint32_t,W*H>;
void paint(Depth& pixels,Rect r,float z) {
    for(long y=(r.y1>0?r.y1:0);y<r.y2&&y<long(H);++y)
        for(long x=(r.x1>0?r.x1:0);x<r.x2&&x<long(W);++x)
            pixels[std::size_t(y)*W+std::size_t(x)]=z;
}
void paint(Color& pixels,Rect r,std::uint32_t argb) {
    for(long y=(r.y1>0?r.y1:0);y<r.y2&&y<long(H);++y)
        for(long x=(r.x1>0?r.x1:0);x<r.x2&&x<long(W);++x)
            pixels[std::size_t(y)*W+std::size_t(x)]=argb;
}
Depth gpu(const GameNativePreDrawDepth& source) {
    assert(source.replay_ready(7,11,13,W,H));
    Depth pixels{};pixels.fill(1.f);
    for(unsigned i=0;i<source.count;++i) {
        const auto& p=source.tiles[i];
        paint(pixels,{long(p.left),long(p.top),long(p.right),long(p.bottom)},p.z);
    }
    return pixels;
}
Color gpu(const GameNativePreDrawFills& source) {
    assert(source.replay_ready(7,11,W,H));
    Color pixels{};pixels.fill(0xff000000u);
    for(unsigned i=0;i<source.count;++i) {
        const auto& p=source.entries[i];
        paint(pixels,{long(p.left),long(p.top),long(p.right),long(p.bottom)},p.argb);
    }
    return pixels;
}
}
int main() {
    GameNativePreDrawDepth depth{};
    Depth expected{};expected.fill(1.f);
    // 32 disjoint authenticated game Z writes can be fully superseded by
    // one later authentic full-viewport Z rectangle, reclaiming GPU slots.
    for(long i=0;i<32;++i){
        const Rect r{i,0,i+1,1};
        assert(depth.record(7,11,13,W,H,0,0,W,H,1,&r,.65f));
        paint(expected,r,.65f);
    }
    assert(depth.count==32u);
    const Rect supersede{0,0,32,1};
    assert(depth.record(7,11,13,W,H,0,0,W,H,1,&supersede,.25f));
    paint(expected,supersede,.25f);
    assert(depth.count==1u);
    assert(gpu(depth)==expected);
    // Mixed partial Z after a newly compacted source is retained in order.
    const Rect stripes[]={{-3,2,12,7},{3,4,15,10},{34,0,51,13}};
    assert(depth.record(7,11,13,W,H,0,0,W,H,3,stripes,.4f));
    for(const Rect& r:stripes)paint(expected,r,.4f);
    assert(gpu(depth)==expected);
    assert(!depth.replay_ready(7,11,14,W,H));
    assert(!depth.record(7,11,14,W,H,0,0,W,H,1,stripes,.1f));
    assert(gpu(depth)==expected);
    // One D3D9 call with 128 repeatedly overlapping source rectangles.
    // The native GPU ledger needs only its final depth region.
    depth.discard();expected.fill(1.f);
    std::array<Rect,GameNativePreDrawDepth::kMaxSourceRects> repeated{};
    for(Rect& r:repeated)r={4,3,24,12};
    assert(depth.record(7,11,13,W,H,0,0,W,H,
        static_cast<std::uint32_t>(repeated.size()),repeated.data(),.3f));
    paint(expected,repeated[0],.3f);
    assert(depth.count==1u && gpu(depth)==expected);
    const auto stable=depth;
    assert(!depth.record(7,11,13,W,H,0,0,W,H,
        static_cast<std::uint32_t>(repeated.size()+1),repeated.data(),.2f));
    const Rect malformed[]={{0,0,2,3},{6,6,6,7}};
    assert(!depth.record(7,11,13,W,H,0,0,W,H,2,malformed,.2f));
    assert(!depth.record(7,11,13,W,H,0,0,W,H,1,repeated.data(),
        std::numeric_limits<float>::quiet_NaN()));
    assert(depth.count==stable.count && gpu(depth)==expected);
    // Combined TARGET|Z must commit or reject both source ledgers together.
    GameNativePreDrawFills colors{};depth.discard();
    Color expectedColor{};expectedColor.fill(0xff000000u);
    expected.fill(1.f);
    constexpr std::uint32_t red=0xffcc2233u;
    assert(GameNativePreDrawCombinedClear::record(
        colors,depth,7,11,13,W,H,0,0,W,H,
        static_cast<std::uint32_t>(repeated.size()),repeated.data(),red,.45f));
    paint(expected,repeated[0],.45f);
    paint(expectedColor,repeated[0],red);
    assert(depth.count==1u && colors.count==1u);
    assert(gpu(depth)==expected && gpu(colors)==expectedColor);
    // A depth-only budget overflow cannot leak any staged color write.
    colors.discard();depth.discard();
    for(long i=0;i<32;++i){
        Rect r{i,0,i+1,1};
        assert(depth.record(7,11,13,W,H,0,0,W,H,1,&r,.75f));
    }
    const Rect disjoint{0,15,1,16};
    assert(!GameNativePreDrawCombinedClear::record(
        colors,depth,7,11,13,W,H,0,0,W,H,1,&disjoint,red,.2f));
    assert(colors.count==0u && depth.count==32u);
    // Different-value intervening writes must not be elided by an older Z.
    depth.discard();expected.fill(1.f);
    Rect block{2,2,12,12};
    assert(depth.record(7,11,13,W,H,0,0,W,H,1,&block,.3f));
    paint(expected,block,.3f);
    Rect inner{3,3,6,6};
    assert(depth.record(7,11,13,W,H,0,0,W,H,1,&inner,.9f));
    paint(expected,inner,.9f);
    assert(depth.record(7,11,13,W,H,0,0,W,H,1,&inner,.3f));
    paint(expected,inner,.3f);
    assert(gpu(depth)==expected);
}
