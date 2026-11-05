// Exact pixel oracle: interleaved successful D3D9 game TARGET|Z rectangles
// become bounded native first-Draw RTV/DSV tiles without changing source order.
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
constexpr unsigned W=80,H=32;
using Color=std::array<std::uint32_t,W*H>;
using Depth=std::array<float,W*H>;
void write(Color& c,Depth& d,Rect r,std::uint32_t argb,float z) {
    for(long y=r.y1;y<r.y2;++y) for(long x=r.x1;x<r.x2;++x) {
        auto i=std::size_t(y)*W+std::size_t(x);c[i]=argb;d[i]=z;
    }
}
void verify(const GameNativePreDrawFills& c,const GameNativePreDrawDepth& d,
            const Color& expectedC,const Depth& expectedZ) {
    assert(c.replay_ready(7,11,W,H));
    assert(d.replay_ready(7,11,13,W,H));
    Color gpuC{};gpuC.fill(0xff000000u);
    Depth gpuZ{};gpuZ.fill(1.f);
    for(unsigned i=0;i<c.count;++i) {
        const auto& t=c.entries[i];
        for(auto y=t.top;y<t.bottom;++y) for(auto x=t.left;x<t.right;++x)
            gpuC[std::size_t(y)*W+std::size_t(x)]=t.argb;
    }
    for(unsigned i=0;i<d.count;++i) {
        const auto& t=d.tiles[i];
        for(auto y=t.top;y<t.bottom;++y) for(auto x=t.left;x<t.right;++x)
            gpuZ[std::size_t(y)*W+std::size_t(x)]=t.z;
    }
    assert(gpuC==expectedC && gpuZ==expectedZ);
}
bool record(GameNativePreDrawFills& c,GameNativePreDrawDepth& d,
            Rect r,std::uint32_t argb,float z) {
    return GameNativePreDrawCombinedClear::record(
        c,d,7,11,13,W,H,0,0,W,H,1,&r,argb,z);
}
}
int main() {
    constexpr std::uint32_t A=0xff903018u,B=0xff1040c0u;
    GameNativePreDrawFills c{};
    GameNativePreDrawDepth d{};
    Color goldC{};goldC.fill(0xff000000u);
    Depth goldZ{};goldZ.fill(1.f);
    // 48 successful source writes in alternating independent game bands.
    // Prior 16-color-tile algorithm could not represent row 9 onward.
    for(long y=0;y<24;++y) {
        Rect a{0,y,8,y+1},b{16,y,24,y+1};
        assert(record(c,d,a,A,.75f));
        assert(record(c,d,b,B,.2f));
        write(goldC,goldZ,a,A,.75f);write(goldC,goldZ,b,B,.2f);
    }
    assert(c.count==2u && d.count==2u);
    verify(c,d,goldC,goldZ);
    // A color/Z write touching a proposed rectangular union is a real
    // chronological barrier. No bounding-box overpaint is permitted.
    GameNativePreDrawFills bc{};
    GameNativePreDrawDepth bd{};
    Color expectedC{};expectedC.fill(0xff000000u);
    Depth expectedZ{};expectedZ.fill(1.f);
    for(const Rect r : {Rect{40,0,48,2},Rect{40,1,48,2},Rect{40,2,48,3}}) {
        const bool middle=r.y1==1;
        auto value=middle?B:A;auto z=middle?.2f:.75f;
        assert(record(bc,bd,r,value,z));
        write(expectedC,expectedZ,r,value,z);
    }
    assert(bc.count==3u && bd.count==3u);
    verify(bc,bd,expectedC,expectedZ);
    // 128 nonfusible pre-first-Draw COLOR regions remain representable;
    // a 129th paired call must fail transactionally with no depth write.
    GameNativePreDrawFills saturated{};
    GameNativePreDrawDepth untouched{};
    for(long i=0;i<128;++i)
        assert(saturated.record(7,11,2*(i%40),i/40,
                                2*(i%40)+1,i/40+1,W,H,
                                A+std::uint32_t(i)));
    const auto before=saturated;
    assert(!record(saturated,untouched,{0,12,1,13},B,.2f));
    assert(untouched.count==0u && saturated.count==before.count);
    for(unsigned i=0;i<before.count;++i) {
        const auto& a=saturated.entries[i];
        const auto& b=before.entries[i];
        assert(a.left==b.left && a.top==b.top &&
               a.right==b.right && a.bottom==b.bottom && a.argb==b.argb);
    }
    // Independent depth COM identity remains enforced.
    const Rect foreign{40,4,41,5};
    assert(!d.record(7,11,14,W,H,0,0,W,H,1,&foreign,.4f));
    // L-shaped equal-value union must not fabricate a third corner.
    GameNativePreDrawFills lc{};
    GameNativePreDrawDepth ld{};
    assert(record(lc,ld,{0,28,4,30},A,.75f));
    assert(record(lc,ld,{2,30,4,32},A,.75f));
    assert(lc.count==2u && ld.count==2u);
}
