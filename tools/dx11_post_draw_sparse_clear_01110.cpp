// 01110: authentic sparse post-Draw TARGET/Z GPU replay batching.
// Test the independent pixel masks and transactional rejection used by both
// D3D11.1 ClearView and ordered D3D11.0 raster fallback.
#include "../src/vr/d3d11/native_game_post_draw_clear_batch.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
struct Rect { long x1,y1,x2,y2; };
int main() {
    using Batch = GameNativePostDrawClearBatch;
    using Region = Batch::Region;
    static_assert(Batch::kMaxGpuRegions == 32u);
    static_assert(Batch::kMaxSourceRects == 128u);
    static_assert(Batch::gpu_chunk_size(0u) == 0u);
    static_assert(Batch::gpu_chunk_size(33u) == 32u);
    static_assert(Batch::gpu_chunk_size(1u) == 1u);
    constexpr std::uint32_t width = 384u;
    constexpr std::uint32_t height = 3u;
    std::array<Rect,128> src{};
    for (std::uint32_t i=0; i<src.size(); ++i)
        src[i]={long(i*3u),0,long(i*3u+2u),3};
    std::array<Region,Batch::kMaxSourceRects> output{};
    std::uint32_t used=0u;
    assert(Batch::build(width,height,0,0,width,height,
                        static_cast<std::uint32_t>(src.size()),
                        src.data(),output,used));
    assert(used==128u); // no source gap may be filled by coalescing
    std::array<std::uint8_t,width*height> color{},depth{},expected{};
    for(std::uint32_t y=0; y<height; ++y)
        for(std::uint32_t x=0; x<width; ++x)
            expected[y*width+x]=(x%3u)!=2u ? 1u : 0u;
    // Same exact bounded region batches for the full game color RTV and
    // D32 attachment; the two calls are separate but cover equal pixels.
    std::uint32_t gpuBatches=0u, gpuRects=0u;
    for (std::uint32_t start=0u; start<used;) {
        const auto count=Batch::gpu_chunk_size(used-start);
        assert(count>=1u && count<=32u);
        for (std::uint32_t j=start; j<start+count; ++j) {
            const Region r=output[j];
            assert(r.left<r.right && r.top<r.bottom);
            for(std::int64_t y=r.top;y<r.bottom;++y)
                for(std::int64_t x=r.left;x<r.right;++x) {
                    color[std::size_t(y)*width+std::size_t(x)]=1u;
                    depth[std::size_t(y)*width+std::size_t(x)]=1u;
                }
        }
        ++gpuBatches;gpuRects+=count;start+=count;
    }
    assert(gpuBatches==4u && gpuRects==128u);
    assert(color==expected && depth==expected);
    // 129 original rectangles or a malformed one cannot partially publish
    // any speculative GPU rects or change the existing output ledger.
    used=7u;output[0]={5,5,6,6};
    std::array<Rect,129> excess{};
    assert(!Batch::build(width,height,0,0,width,height,129u,
                         excess.data(),output,used));
    assert(used==7u && output[0].left==5);
    auto bad=src;bad[63].x2=bad[63].x1;
    assert(!Batch::build(width,height,0,0,width,height,128u,
                         bad.data(),output,used));
    assert(used==7u && output[0].left==5);
    // Authentic 128-rectangle post-Draw TARGET|Z can be entirely outside
    // the viewport even though a native menu/race Draw is pending. Both
    // attachments must remain untouched, regardless of native DSV readiness.
    std::array<Rect,128> outside{};
    for(std::uint32_t i=0;i<outside.size();++i)
        outside[i]={long(width+2u*i),0,long(width+2u*i+1u),3};
    const auto beforeColor=color,beforeDepth=depth;
    assert(Batch::build(width,height,0,0,width,height,128u,
                        outside.data(),output,used) && used==0u);
    assert(color==beforeColor && depth==beforeDepth);
    // A mixed source transaction is NOT a no-op: exactly one clipped native
    // pixel is updated, while the other 127 regions write nothing.
    outside[87]={7,1,8,2};
    assert(Batch::build(width,height,0,0,width,height,128u,
                        outside.data(),output,used) && used==1u);
    assert(output[0].left==7 && output[0].right==8 &&
           output[0].top==1 && output[0].bottom==2);
    // Malformed late source rectangle remains atomic even with earlier
    // valid regions (the caller's ledger is unchanged on failure).
    outside[126].x2=outside[126].x1;
    const auto previous=output[0];
    assert(!Batch::build(width,height,0,0,width,height,128u,
                         outside.data(),output,used));
    assert(used==1u && output[0].left==previous.left);
}
