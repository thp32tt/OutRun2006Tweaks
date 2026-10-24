#include "../src/vr/d3d11/native_game_present_region.hpp"
#include "../src/vr/d3d11/native_game_frame_upload.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
static_assert(GameNativePresentRegion{320,180,1600,900}.partial_backbuffer_source(1920,1080));
static_assert(GameNativePresentRegion{0,0,1280,720}.partial_backbuffer_source(1920,1080));
static_assert(!GameNativePresentRegion{0,0,1920,1080}.partial_backbuffer_source(1920,1080));
static_assert(!GameNativePresentRegion{-1,0,1600,900}.partial_backbuffer_source(1920,1080));
static_assert(!GameNativePresentRegion{0,0,1921,1080}.partial_backbuffer_source(1920,1080));
static_assert(!GameNativePresentRegion{320,180,320,900}.partial_backbuffer_source(1920,1080));
static_assert(!GameNativePresentRegion{320,180,1600,900}.partial_backbuffer_source(0,1080));
int main() {
    constexpr unsigned width=6, height=4, sourcePitch=28;
    constexpr int destPitch=32;
    std::array<unsigned char, destPitch*height> destination{};
    std::array<unsigned char, sourcePitch*height> source{};
    destination.fill(0xA6);
    for (unsigned y=0; y<height; ++y)
        for (unsigned x=0; x<width*4; ++x)
            source[y*sourcePitch+x]=static_cast<unsigned char>((x+y*7)&255u);
    // Both no dirty region and whole-backbuffer dirty must publish only the
    // actual source crop; future partial D3D9 Presents can reuse outer pixels.
    const GameNativePresentRegion visible{1,1,5,3};
    assert(visible.partial_backbuffer_source(width,height));
    assert(GameNativeFrameUpload::copy_rect(destination.data(),destPitch,
        source.data(),sourcePitch,width,height,1,1,5,3));
    for (unsigned y=0; y<height; ++y)
        for (unsigned x=0; x<destPitch; ++x) {
            const bool inside=y>=1 && y<3 && x>=4 && x<20;
            assert(destination[y*destPitch+x]==(inside?source[y*sourcePitch+x]:0xA6));
        }
    const auto snapshot=destination;
    assert(!GameNativeFrameUpload::copy_rect(destination.data(),destPitch,
        source.data(),sourcePitch,width,height,1,1,7,3));
    assert(destination==snapshot);
    assert(!GameNativeFrameUpload::copy_rect(destination.data(),destPitch,
        source.data(),sourcePitch,width,height,4,2,4,3));
    assert(destination==snapshot);
}
