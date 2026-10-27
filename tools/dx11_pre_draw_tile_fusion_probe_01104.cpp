// Authentic game pre-Draw ColorFill/TARGET|Z Clear -> native ordered
// GPU RTV+DSV tile replay. Equivalent rectangular unions fit bounded
// capacity; nonrectangular/interleaved writes remain fail-closed.
#include "../src/vr/d3d11/native_game_pre_draw_combined_clear.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstddef>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
constexpr unsigned W=80,H=24;
using C=std::array<std::uint32_t,W*H>;
using Z=std::array<float,W*H>;
void color(C& a,Rect r,std::uint32_t v){
    for(long y=r.y1;y<r.y2;++y)for(long x=r.x1;x<r.x2;++x)
        a[std::size_t(y)*W+std::size_t(x)]=v;
}
void depth(Z& a,Rect r,float v){
    for(long y=r.y1;y<r.y2;++y)for(long x=r.x1;x<r.x2;++x)
        a[std::size_t(y)*W+std::size_t(x)]=v;
}
void equal(const GameNativePreDrawFills& c,const GameNativePreDrawDepth& z,
           const C& expectedColor,const Z& expectedDepth){
    assert(c.replay_ready(7,11,W,H));
    assert(z.replay_ready(7,11,13,W,H));
    C actualColor{};actualColor.fill(0xff000000u);
    Z actualDepth{};actualDepth.fill(1.f);
    for(unsigned i=0;i<c.count;++i){
        const auto& t=c.entries[i];
        color(actualColor,{long(t.left),long(t.top),long(t.right),long(t.bottom)},t.argb);
    }
    for(unsigned i=0;i<z.count;++i){
        const auto& t=z.tiles[i];
        depth(actualDepth,{long(t.left),long(t.top),long(t.right),long(t.bottom)},t.z);
    }
    assert(actualColor==expectedColor && actualDepth==expectedDepth);
}
}
int main(){
    GameNativePreDrawFills colors{};
    GameNativePreDrawDepth depths{};
    C expectedColor{};expectedColor.fill(0xff000000u);
    Z expectedDepth{};expectedDepth.fill(1.f);
    constexpr std::uint32_t red=0xffb04020u, blue=0xff2050d0u;
    // 128 real source rects form one contiguous viewport strip. Previously
    // overflowed both 16 RTV tiles and 32 DSV tiles; current native GPU
    // first Draw now receives the exact final D3D9 source pixels.
    std::array<Rect,128> strip{};
    for(unsigned i=0;i<strip.size();++i)
        strip[i]={long(i%64u),long(i/64u),long(i%64u+1u),long(i/64u+1u)};
    assert(GameNativePreDrawCombinedClear::record(
        colors,depths,7,11,13,W,H,0,0,W,H,
        unsigned(strip.size()),strip.data(),red,.75f));
    for(const Rect& r:strip){color(expectedColor,r,red);depth(expectedDepth,r,.75f);}
    assert(colors.count==1u && depths.count==1u);
    equal(colors,depths,expectedColor,expectedDepth);
    // A new different-Z/ARGB rectangle must overlay (not contaminate)
    // the earlier retained pixels; subsequent same-valued adjacent pieces
    // may coalesce without skipping the intervening overwrite.
    const Rect middle{8,0,22,2};
    assert(GameNativePreDrawCombinedClear::record(
        colors,depths,7,11,13,W,H,0,0,W,H,1,&middle,blue,.2f));
    color(expectedColor,middle,blue);depth(expectedDepth,middle,.2f);
    const Rect tail{64,0,72,2};
    assert(GameNativePreDrawCombinedClear::record(
        colors,depths,7,11,13,W,H,0,0,W,H,1,&tail,blue,.2f));
    color(expectedColor,tail,blue);depth(expectedDepth,tail,.2f);
    equal(colors,depths,expectedColor,expectedDepth);
    // Adjacent-only merger may not turn an L shape into a filled bounding box.
    GameNativePreDrawFills lcolor{};
    GameNativePreDrawDepth ldepth{};
    C lc{};lc.fill(0xff000000u);Z lz{};lz.fill(1.f);
    const Rect l1{0,8,8,10}, l2{6,10,8,14};
    for(const Rect r : {l1,l2}){
        assert(GameNativePreDrawCombinedClear::record(
            lcolor,ldepth,7,11,13,W,H,0,0,W,H,1,&r,red,.3f));
        color(lc,r,red);depth(lz,r,.3f);
    }
    assert(lcolor.count==2u && ldepth.count==2u);
    equal(lcolor,ldepth,lc,lz);
    // Seventeen distinct game COLOR writes now remain intact for their
    // first-Draw native RTV/DSV replay rather than failing at old tile 16.
    GameNativePreDrawFills fullColor{};
    GameNativePreDrawDepth isolatedZ{};
    for(unsigned i=0;i<16u;++i)
        assert(fullColor.record(7,11,i*2,17,i*2+1,18,W,H,red));
    const Rect seventeenth{34,17,35,18};
    assert(GameNativePreDrawCombinedClear::record(
        fullColor,isolatedZ,7,11,13,W,H,0,0,W,H,1,&seventeenth,red,.6f));
    assert(fullColor.count==17u && isolatedZ.count==1u);
    // A foreign device must not consolidate or change original owner tiles.
    assert(!colors.record(8,11,72,0,73,1,W,H,red));
    assert(!depths.record(7,11,14,W,H,0,0,W,H,1,&middle,.5f));
    equal(colors,depths,expectedColor,expectedDepth);
}
