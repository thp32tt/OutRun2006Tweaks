#include "../src/vr/d3d11/live_game_render_target_readback.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
using native_rt_readback::Layout;
static_assert(native_rt_readback::sampleable(Layout::rgb565,false));
static_assert(native_rt_readback::sampleable(Layout::argb1555,false));
static_assert(native_rt_readback::sampleable(Layout::argb4444,false));
static_assert(native_rt_readback::sampleable(Layout::xrgb1555,false));
static_assert(native_rt_readback::sampleable(Layout::xrgb4444,false));
static_assert(!native_rt_readback::sampleable(Layout::rgb565,true));
static_assert(!native_rt_readback::sampleable(Layout::argb1555,true));
static_assert(!native_rt_readback::sampleable(Layout::argb4444,true));
static_assert(!native_rt_readback::sampleable(Layout::xrgb1555,true));
static_assert(!native_rt_readback::sampleable(Layout::xrgb4444,true));
static_assert(!native_rt_readback::sampleable(Layout::unsupported,false));
int main() {
    const std::array<std::uint8_t,6> rgb{{0,0xf8, 0xe0,7, 0x1f,0}};
    std::array<std::uint8_t,12> pixels{};
    assert(native_rt_readback::unpack_row(rgb.data(),pixels.data(),3,Layout::rgb565));
    assert((pixels==std::array<std::uint8_t,12>{{0,0,255,255, 0,255,0,255, 255,0,0,255}}));
    const std::array<std::uint8_t,4> alpha{{0x1f,0, 0,0xfc}};
    assert(native_rt_readback::unpack_row(alpha.data(),pixels.data(),2,Layout::argb1555));
    assert(pixels[0]==255 && pixels[1]==0 && pixels[2]==0 && pixels[3]==0);
    assert(pixels[4]==0 && pixels[5]==0 && pixels[6]==255 && pixels[7]==255);
    assert(native_rt_readback::unpack_row(alpha.data(),pixels.data(),2,Layout::xrgb1555));
    assert(pixels[3]==255 && pixels[7]==255);
    const std::array<std::uint8_t,2> nibble{{0x21,0x43}};
    assert(native_rt_readback::unpack_row(nibble.data(),pixels.data(),1,Layout::argb4444));
    assert(pixels[0]==17 && pixels[1]==34 && pixels[2]==51 && pixels[3]==68);
    assert(native_rt_readback::unpack_row(nibble.data(),pixels.data(),1,Layout::xrgb4444));
    assert(pixels[0]==17 && pixels[1]==34 && pixels[2]==51 && pixels[3]==255);
    pixels.fill(0x5a);
    assert(!native_rt_readback::unpack_row(nullptr,pixels.data(),1,Layout::rgb565));
    assert(!native_rt_readback::unpack_row(rgb.data(),nullptr,1,Layout::rgb565));
    assert(!native_rt_readback::unpack_row(rgb.data(),pixels.data(),0,Layout::rgb565));
    assert(!native_rt_readback::unpack_row(rgb.data(),pixels.data(),1,Layout::unsupported));
    for(auto x:pixels) assert(x==0x5a);
    assert(native_rt_readback::sampleable(Layout::argb8,true));
    assert(!native_rt_readback::sampleable(Layout::a2r10g10b10,true));
}
