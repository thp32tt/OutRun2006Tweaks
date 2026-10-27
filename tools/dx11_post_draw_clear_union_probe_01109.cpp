// 01109: integrated post-Draw original D3D9 TARGET/Z 128-source rectangle
// compaction into exactly equivalent native RTV/D32 GPU ClearView/raster tiles.
#include "../src/vr/d3d11/native_game_post_draw_clear_batch.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
namespace {
struct Rect { long x1,y1,x2,y2; };
using Batch = GameNativePostDrawClearBatch;
using Region = Batch::Region;
bool equals(Region r, std::int64_t l, std::int64_t t,
            std::int64_t x, std::int64_t b) {
    return r.left==l && r.top==t && r.right==x && r.bottom==b;
}
template<std::size_t N>
bool pack(const std::array<Rect,N>& source, std::uint32_t w,
          std::uint32_t h, std::array<Region,Batch::kMaxGpuRegions>& output,
          std::uint32_t& count) {
    return Batch::build(w,h,0,0,w,h,static_cast<std::uint32_t>(N),
                        source.data(),output,count);
}
}
int main() {
    static_assert(Batch::kMaxSourceRects == 128u);
    static_assert(Batch::kMaxGpuRegions == 32u);
    std::array<Region,Batch::kMaxGpuRegions> gpu{};
    std::uint32_t used=99u;
    std::array<Rect,128> vertical{};
    for(std::size_t i=0;i<vertical.size();++i)
        vertical[i]={long(i*2u),0,long(i*2u+2u),8};
    assert(pack(vertical,256,8,gpu,used));
    assert(used==1u && equals(gpu[0],0,0,256,8));
    // Two rows in intentionally interleaved source order must form one
    // actual rectangular union, including post-Draw TARGET|Z shared tiles.
    std::array<Rect,128> mosaic{};
    for(std::size_t i=0;i<64u;++i) {
        mosaic[i*2u]={long(i*2u),0,long(i*2u+2u),4};
        mosaic[i*2u+1u]={long(i*2u),4,long(i*2u+2u),8};
    }
    assert(pack(mosaic,128,8,gpu,used));
    assert(used==1u && equals(gpu[0],0,0,128,8));
    // D3D9 viewport clips signed source coordinates; empty rects count as
    // no-ops, without clearing unrelated game screen pixels.
    std::array<Rect,3> clipped{{{-20,-10,2,8},{2,0,4,8},{100,100,110,110}}};
    assert(pack(clipped,4,8,gpu,used));
    assert(used==1u && equals(gpu[0],0,0,4,8));
    // A nonrectangular L union must NEVER become a bounding box.
    std::array<Rect,2> lshape{{{0,0,4,2},{0,2,2,4}}};
    assert(pack(lshape,4,4,gpu,used));
    assert(used==2u);
    // 33 separated real color/Z writes cannot fit the existing 32 GPU
    // budget. Return failure without modifying the prior output ledger.
    std::array<Rect,33> islands{};
    for(std::size_t i=0;i<islands.size();++i)
        islands[i]={long(i*4u),0,long(i*4u+2u),2};
    used=7u;gpu[0]={7,7,8,8};
    assert(!pack(islands,132,2,gpu,used));
    assert(used==7u && equals(gpu[0],7,7,8,8));
    auto malformed=vertical;malformed[18].x1=malformed[18].x2;
    assert(!pack(malformed,256,8,gpu,used));
    assert(used==7u);
    std::array<Rect,129> tooMany{};
    assert(!pack(tooMany,256,8,gpu,used));
    assert(used==7u);
    assert(Batch::build(20u,10u,2u,3u,15u,5u,0u,
        static_cast<const Rect*>(nullptr),gpu,used));
    assert(used==1u && equals(gpu[0],2,3,17,8));
    assert(!Batch::build(20u,10u,2u,3u,0u,5u,0u,
        static_cast<const Rect*>(nullptr),gpu,used));
    assert(used==1u);
    return 0;
}
