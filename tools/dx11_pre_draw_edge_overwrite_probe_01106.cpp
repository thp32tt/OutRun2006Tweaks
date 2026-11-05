// D3D9 menu/car/race pre-Draw partial TARGET|Z overwrites must exactly
// match first native D3D11 RTV/D32 replay, without redundant edge pixels.
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstddef>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
constexpr unsigned W=40,H=20;
using C=std::array<std::uint32_t,W*H>;
using D=std::array<float,W*H>;
void paint(C& c,D& d,Rect r,std::uint32_t argb,float z) {
    for(long y=r.y1;y<r.y2;++y)
        for(long x=r.x1;x<r.x2;++x) {
            const auto offset=std::size_t(y)*W+std::size_t(x);
            c[offset]=argb;d[offset]=z;
        }
}
bool add(GameNativePreDrawFills& c,GameNativePreDrawDepth& d,
         Rect r,std::uint32_t argb,float z) {
    return GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,0,0,W,H,1,&r,argb,z);
}
void exact(const GameNativePreDrawFills& c,const GameNativePreDrawDepth& d,
           const C& expectedC,const D& expectedD) {
    assert(c.replay_ready(7,11,W,H) && d.replay_ready(7,11,13,W,H));
    C pixels{};pixels.fill(0xff000000);
    D depth{};depth.fill(1.f);
    for(unsigned i=0;i<c.count;++i) {
        const auto& r=c.entries[i];
        for(auto y=r.top;y<r.bottom;++y)
            for(auto x=r.left;x<r.right;++x)
                pixels[std::size_t(y)*W+std::size_t(x)]=r.argb;
    }
    for(unsigned i=0;i<d.count;++i) {
        const auto& r=d.tiles[i];
        for(auto y=r.top;y<r.bottom;++y)
            for(auto x=r.left;x<r.right;++x)
                depth[std::size_t(y)*W+std::size_t(x)]=r.z;
    }
    assert(pixels==expectedC && depth==expectedD);
}
}
int main() {
    constexpr std::uint32_t A=0xff124488u,B=0xff883322u,
                            C1=0xff115522u,D1=0xff664411u,E=0xff225588u;
    GameNativePreDrawFills color{};
    GameNativePreDrawDepth depth{};
    C goldC{};goldC.fill(0xff000000);
    D goldD{};goldD.fill(1.f);
    auto source=[&](Rect r,std::uint32_t c,float z) {
        assert(add(color,depth,r,c,z));
        paint(goldC,goldD,r,c,z);
        exact(color,depth,goldC,goldD);
    };
    // Authentic game prefix: newest Clears peel the top, right, bottom
    // and left sides of an earlier RT/Z region before the first Draw.
    source({0,0,12,12},A,.8f);
    source({0,0,12,4},B,.7f);
    assert(color.entries[0].top==4 && depth.tiles[0].top==4);
    source({8,4,12,12},C1,.6f);
    assert(color.entries[0].right==8 && depth.tiles[0].right==8);
    source({0,10,8,12},D1,.5f);
    assert(color.entries[0].bottom==10 && depth.tiles[0].bottom==10);
    source({0,4,2,10},E,.4f);
    assert(color.entries[0].left==2 && depth.tiles[0].left==2);
    assert(color.count==5u && depth.count==5u);
    // Interior overlap would split an earlier rectangle into four.
    // Never fabricate one residual via bounding-box overpaint.
    source({4,6,6,8},B,.3f);
    assert(color.count==6u && depth.count==6u);
    assert(color.entries[0].left==2 && color.entries[0].right==8);
    // A foreign depth attachment fails atomically, preserving native tiles
    // and original game's D3D9 fallback.
    const Rect foreign{20,0,24,4};
    auto beforeC=color;auto beforeD=depth;
    assert(!GameNativePreDrawCombinedClear::record(
        color,depth,7,11,14,W,H,0,0,W,H,1,&foreign,A,.2f));
    assert(color.count==beforeC.count && depth.count==beforeD.count);
    exact(color,depth,goldC,goldD);
}
