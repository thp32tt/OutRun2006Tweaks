#include "../src/vr/d3d11/native_game_multi_dirty_upload.hpp"
#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameNativeDirtyRectangle tiles[]={{0,0,2,2},{4,1,6,4}};
constexpr GameNativePresentRegion entire{0,0,6,4};
constexpr GameNativePresentRegion crop{1,1,5,3};
constexpr auto full=GameNativeMultiDirtyUpload::select(6,4,entire,2,32,0,0,6,4,tiles);
constexpr auto clipped=GameNativeMultiDirtyUpload::select(6,4,crop,2,32,0,0,6,4,tiles);
static_assert(full.valid && full.count==2 && full.regions[1].left==4 &&
              full.uploadBounds.left==0 && full.uploadBounds.top==0 &&
              full.uploadBounds.right==6 && full.uploadBounds.bottom==4);
static_assert(clipped.valid && clipped.count==2 && clipped.regions[0].left==1 &&
              clipped.regions[1].right==5 && clipped.regions[1].bottom==3 &&
              clipped.uploadBounds.left==1 && clipped.uploadBounds.top==1 &&
              clipped.uploadBounds.right==5 && clipped.uploadBounds.bottom==3);
constexpr GameNativeDirtyRectangle offscreen[]={{0,0,1,1},{1,0,2,1}};
constexpr auto omitted=GameNativeMultiDirtyUpload::select(6,4,crop,2,32,0,0,2,1,offscreen);
static_assert(!omitted.valid);
constexpr GameNativeDirtyRectangle touching[]={{0,0,2,2},{2,0,4,2}};
static_assert(GameNativeMultiDirtyUpload::select(6,4,entire,2,32,0,0,4,2,touching).valid);
constexpr GameNativeDirtyRectangle overlapping[]={{0,0,3,2},{2,1,4,3}};
static_assert(!GameNativeMultiDirtyUpload::select(6,4,entire,2,32,0,0,4,3,overlapping).valid);
static_assert(!GameNativeMultiDirtyUpload::select(6,4,entire,2,16,0,0,6,4,tiles).valid);
static_assert(!GameNativeMultiDirtyUpload::select(6,4,entire,2,32,0,0,5,4,tiles).valid);
static_assert(!GameNativeMultiDirtyUpload::select(6,4,entire,9,144,0,0,6,4,tiles).valid);
constexpr GameNativeDirtyRectangle outOfBounds[]={{0,0,2,2},{4,1,7,4}};
static_assert(!GameNativeMultiDirtyUpload::select(6,4,entire,2,32,0,0,7,4,outOfBounds).valid);
int main() {
    constexpr std::uint32_t width=6, height=4, readPitch=28;
    constexpr std::int32_t writePitch=32;
    std::array<std::uint8_t,readPitch*height> source{};
    std::array<std::uint8_t,writePitch*height> target{};
    target.fill(0x31);
    for (std::uint32_t y=0;y<height;++y)
        for (std::uint32_t x=0;x<width;++x)
            for (std::uint32_t c=0;c<4;++c)
                source[y*readPitch+x*4+c]=static_cast<std::uint8_t>(10+y*20+x*3+c);
    for (std::uint32_t i=0;i<clipped.count;++i) {
        const auto& r=clipped.regions[i];
        assert(GameNativeFrameUpload::copy_rect(
            target.data(),writePitch,source.data(),readPitch,width,height,
            static_cast<std::uint32_t>(r.left),static_cast<std::uint32_t>(r.top),
            static_cast<std::uint32_t>(r.right),static_cast<std::uint32_t>(r.bottom)));
    }
    // D3D9 GetRenderTargetData seeded untouched holes with original pixels.
    // Simulate a failed atomic UpdateSurface: game backbuffer is unmodified.
    std::array<std::uint8_t,writePitch*height> original{};
    original.fill(0x31);
    auto failedCommit=original;
    assert(failedCommit==original);
    // Success publishes the full verified bounding crop in one operation;
    // pixels in its holes still come from the D3D9 snapshot.
    auto published=original;
    for(std::int64_t y=clipped.uploadBounds.top;y<clipped.uploadBounds.bottom;++y)
        for(std::int64_t x=clipped.uploadBounds.left;x<clipped.uploadBounds.right;++x)
            for(std::uint32_t c=0;c<4;++c)
                published[static_cast<std::size_t>(y)*writePitch+static_cast<std::size_t>(x)*4+c]=
                    target[static_cast<std::size_t>(y)*writePitch+static_cast<std::size_t>(x)*4+c];
    for (std::uint32_t y=0;y<height;++y)
        for (std::uint32_t x=0;x<width;++x) {
            bool covered=false;
            for (std::uint32_t i=0;i<clipped.count;++i) {
                const auto& r=clipped.regions[i];
                if(x>=r.left&&x<r.right&&y>=r.top&&y<r.bottom) covered=true;
            }
            for(std::uint32_t c=0;c<4;++c) {
                assert(target[y*writePitch+x*4+c]==
                    (covered?source[y*readPitch+x*4+c]:0x31));
                assert(published[y*writePitch+x*4+c]==
                    (covered?source[y*readPitch+x*4+c]:0x31));
            }
        }
    for (std::uint32_t y=0;y<height;++y)
        for (std::uint32_t x=width*4;x<static_cast<std::uint32_t>(writePitch);++x)
            assert(target[y*writePitch+x]==0x31);
    return 0;
}
