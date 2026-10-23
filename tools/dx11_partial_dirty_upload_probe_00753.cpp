#include "../src/vr/d3d11/native_game_partial_dirty_upload.hpp"
#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameNativePresentRegion full{0,0,6,4};
constexpr GameNativePresentRegion crop{1,1,5,3};
constexpr auto sub = GameNativePartialDirtyUpload::select(6,4,full,1,16,1,1,4,3,1,1,4,3);
static_assert(sub.valid && sub.source.left == 1 && sub.source.top == 1 &&
              sub.source.right == 4 && sub.source.bottom == 3);
constexpr auto clipped = GameNativePartialDirtyUpload::select(6,4,crop,1,16,0,0,4,2,0,0,4,2);
static_assert(clipped.valid && clipped.source.left == 1 && clipped.source.top == 1 &&
              clipped.source.right == 4 && clipped.source.bottom == 2);
static_assert(!GameNativePartialDirtyUpload::select(6,4,crop,1,16,0,0,1,1,0,0,1,1).valid);
static_assert(!GameNativePartialDirtyUpload::select(6,4,crop,1,16,0,0,7,2,0,0,7,2).valid);
static_assert(!GameNativePartialDirtyUpload::select(6,4,crop,1,16,0,0,4,2,0,0,5,2).valid);
static_assert(!GameNativePartialDirtyUpload::select(6,4,crop,2,32,0,0,4,2,0,0,4,2).valid);
static_assert(!GameNativePartialDirtyUpload::select(6,4,crop,1,8,0,0,4,2,0,0,4,2).valid);
static_assert(!GameNativePartialDirtyUpload::select(6,4,{-1,0,5,3},1,16,0,0,4,2,0,0,4,2).valid);
static_assert(!GameNativePartialDirtyUpload::select(6,4,crop,1,16,2,2,2,4,2,2,2,4).valid);
int main() {
    constexpr unsigned width=6, height=4, sourcePitch=28;
    constexpr int destPitch=32;
    std::array<unsigned char,destPitch*height> dest{};
    std::array<unsigned char,sourcePitch*height> source{};
    dest.fill(0xA6);
    for(unsigned y=0;y<height;++y)
      for(unsigned x=0;x<width*4;++x)
        source[y*sourcePitch+x]=static_cast<unsigned char>((x+y*13)&255u);
    // Native frame readback -> CPU upload -> bounded D3D9 UpdateSurface RECT.
    assert(GameNativeFrameUpload::copy_rect(dest.data(),destPitch,
        source.data(),sourcePitch,width,height,
        static_cast<unsigned>(clipped.source.left),static_cast<unsigned>(clipped.source.top),
        static_cast<unsigned>(clipped.source.right),static_cast<unsigned>(clipped.source.bottom)));
    for(unsigned y=0;y<height;++y)
      for(unsigned x=0;x<destPitch;++x) {
        const bool uploaded=y==1 && x>=4 && x<16;
        assert(dest[y*destPitch+x]==(uploaded?source[y*sourcePitch+x]:0xA6));
      }
    const auto snapshot=dest;
    const auto invalid=GameNativePartialDirtyUpload::select(6,4,crop,1,16,0,0,7,2,0,0,7,2);
    if(invalid.valid) (void)GameNativeFrameUpload::copy_rect(dest.data(),destPitch,
        source.data(),sourcePitch,width,height,
        static_cast<unsigned>(invalid.source.left),static_cast<unsigned>(invalid.source.top),
        static_cast<unsigned>(invalid.source.right),static_cast<unsigned>(invalid.source.bottom));
    assert(dest==snapshot);
}
