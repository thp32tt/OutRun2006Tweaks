// Authentic game partial TARGET|ZBUFFER Clear -> separate native GPU color
// and depth pre-Draw replay, committed atomically only when both fit.
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include "../src/vr/d3d11/native_game_pre_draw_replay.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1, y1, x2, y2; };
constexpr std::uint32_t W=40, H=18;
using Color=std::array<std::uint32_t,W*H>;
using Depth=std::array<float,W*H>;
void paint(Color& f, int l,int t,int r,int b,std::uint32_t v) {
    for(int y=t;y<b;++y)for(int x=l;x<r;++x)f[std::size_t(y)*W+x]=v;
}
void paint(Depth& f, int l,int t,int r,int b,float v) {
    for(int y=t;y<b;++y)for(int x=l;x<r;++x)f[std::size_t(y)*W+x]=v;
}
std::uint32_t pack(const GameNativePreDrawTile& t) {
    const auto b=[](float v){return std::uint32_t(v*255.f+.5f);};
    return (b(t.rgba[3])<<24)|(b(t.rgba[0])<<16)|
           (b(t.rgba[1])<<8)|b(t.rgba[2]);
}
Color gpuColors(const GameNativePreDrawFills& src) {
    Color out{}; out.fill(0xff000000u);
    auto gpu=[&](const GameNativePreDrawTile& t) noexcept {
        paint(out,int(t.left),int(t.top),int(t.right),int(t.bottom),pack(t));
        return true;
    };
    assert(game_native_replay_pre_draw_fills(src,7,11,W,H,false,true,gpu,gpu));
    return out;
}
Depth gpuDepths(const GameNativePreDrawDepth& src) {
    Depth out{};out.fill(1.f);
    assert(src.replay_ready(7,11,13,W,H));
    for(std::uint32_t i=0;i<src.count;++i){
        const auto& t=src.tiles[i];
        paint(out,int(t.left),int(t.top),int(t.right),int(t.bottom),t.z);
    }
    return out;
}
}
int main() {
    GameNativePreDrawFills c{};GameNativePreDrawDepth d{};
    Color ec{};ec.fill(0xff000000u);
    Depth ed{};ed.fill(1.f);
    // The source has earlier successful COLOR and Z calls in the same seed.
    assert(c.record(7,11,0,0,20,8,W,H,0xff112233u));
    paint(ec,0,0,20,8,0xff112233u);
    const Rect older[]={{2,0,8,3}};
    assert(d.record(7,11,13,W,H,0,0,W,H,1,older,.75f));
    paint(ed,2,0,8,3,.75f);
    // Two partly out-of-viewport D3DRECTs are clipped at the source.
    const Rect paired[]={{-20,-10,10,6},{14,6,45,22}};
    assert(GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,4,2,24,12,2,paired,0xffaabbccu,.3f));
    paint(ec,4,2,10,6,0xffaabbccu);paint(ed,4,2,10,6,.3f);
    paint(ec,14,6,28,14,0xffaabbccu);paint(ed,14,6,28,14,.3f);
    assert(gpuColors(c)==ec && gpuDepths(d)==ed);
    // One Clear without source rectangles means viewport, not backbuffer.
    assert(GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,0,12,8,4,0,static_cast<const Rect*>(nullptr),
        0xff334455u,.9f));
    paint(ec,0,12,8,16,0xff334455u);paint(ed,0,12,8,16,.9f);
    assert(gpuColors(c)==ec && gpuDepths(d)==ed);
    auto colorsBefore=gpuColors(c);auto depthsBefore=gpuDepths(d);
    const auto cc=c.count,dc=d.count;
    const Rect bad[]={{3,3,7,5},{8,8,2,9}};
    assert(!GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,0,0,W,H,2,bad,0xff445566u,.2f));
    assert(!GameNativePreDrawCombinedClear::record(
        c,d,7,11,14,W,H,0,0,W,H,1,paired,0xff445566u,.2f));
    assert(!GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,0,0,W,H,1,paired,0xff445566u,
        std::numeric_limits<float>::quiet_NaN()));
    assert(cc==c.count&&dc==d.count);
    assert(gpuColors(c)==colorsBefore&&gpuDepths(d)==depthsBefore);
    // A no-pixel game Clear consumes neither color nor depth slots.
    const Rect outside[]={{100,100,102,102}};
    assert(GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,0,0,W,H,1,outside,0xff010203u,.1f));
    assert(cc==c.count&&dc==d.count);
    // Color transaction succeeds, but depth has only 32 GPU replay slots.
    // Failure of the second recorder must roll back FIRST recorder too.
    GameNativePreDrawFills stagedColor{};
    GameNativePreDrawDepth stagedDepth{};
    for(int i=0;i<32;++i){
        Rect r{long(i),0,long(i+1),1};
        assert(stagedDepth.record(7,11,13,W,H,0,0,W,H,1,&r,(i&1)? .5f : .6f));
    }
    const Rect novel[]={{0,4,3,7}};
    const auto priorDepth=stagedDepth.count;
    assert(!GameNativePreDrawCombinedClear::record(
        stagedColor,stagedDepth,7,11,13,W,H,0,0,W,H,1,novel,
        0xffa0b0c0u,.4f));
    assert(stagedColor.count==0&&stagedDepth.count==priorDepth);
    // Color tile budget overflow must likewise preserve existing depth.
    stagedColor.discard();stagedDepth.discard();
    for(int i=0;i<16;++i)
        assert(stagedColor.record(7,11,i*2,0,i*2+1,1,W,H,0xff121212u));
    assert(!GameNativePreDrawCombinedClear::record(
        stagedColor,stagedDepth,7,11,13,W,H,0,0,W,H,1,novel,
        0xff454545u,.4f));
    assert(stagedDepth.count==0u&&stagedColor.count==16u);
}
