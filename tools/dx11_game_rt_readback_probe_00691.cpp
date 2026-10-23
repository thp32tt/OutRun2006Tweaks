#include "../src/vr/d3d11/live_game_render_target_readback.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
using native_rt_readback::Layout;
static_assert(native_rt_readback::sampleable(Layout::argb8, true));
static_assert(native_rt_readback::sampleable(Layout::xrgb8, false));
static_assert(native_rt_readback::sampleable(Layout::a8b8g8r8, true));
static_assert(native_rt_readback::sampleable(Layout::x8b8g8r8, false));
static_assert(native_rt_readback::sampleable(Layout::a2r10g10b10, false));
static_assert(native_rt_readback::sampleable(Layout::a2b10g10r10, false));
static_assert(!native_rt_readback::sampleable(Layout::a2r10g10b10, true));
static_assert(!native_rt_readback::sampleable(Layout::a2b10g10r10, true));
static_assert(!native_rt_readback::sampleable(Layout::unsupported, false));
int main() {
    const std::array<std::uint8_t, 12> rgba{{12,34,56,78,90,123,145,167,201,202,203,204}};
    std::array<std::uint8_t, 8> bgra{};
    assert(native_rt_readback::unpack_row(rgba.data(),bgra.data(),2,Layout::a8b8g8r8));
    assert((bgra==std::array<std::uint8_t,8>{{56,34,12,78,145,123,90,167}}));
    assert(native_rt_readback::unpack_row(rgba.data(),bgra.data(),2,Layout::x8b8g8r8));
    assert((bgra==std::array<std::uint8_t,8>{{56,34,12,255,145,123,90,255}}));
    assert(native_rt_readback::unpack_row(rgba.data(),bgra.data(),2,Layout::argb8));
    assert((bgra==std::array<std::uint8_t,8>{{12,34,56,78,90,123,145,167}}));
    assert(native_rt_readback::unpack_row(rgba.data(),bgra.data(),2,Layout::xrgb8));
    assert((bgra==std::array<std::uint8_t,8>{{12,34,56,255,90,123,145,255}}));
    std::array<std::uint8_t, 4> ten{{255,3,0,192}};
    assert(native_rt_readback::unpack_row(ten.data(),bgra.data(),1,Layout::a2r10g10b10));
    assert((std::array<std::uint8_t,4>{{bgra[0],bgra[1],bgra[2],bgra[3]}} ==
            std::array<std::uint8_t,4>{{255,0,0,255}}));
    assert(native_rt_readback::unpack_row(ten.data(),bgra.data(),1,Layout::a2b10g10r10));
    assert((std::array<std::uint8_t,4>{{bgra[0],bgra[1],bgra[2],bgra[3]}} ==
            std::array<std::uint8_t,4>{{0,0,255,255}}));
    bgra.fill(123);
    assert(!native_rt_readback::unpack_row(nullptr,bgra.data(),1,Layout::argb8));
    assert(!native_rt_readback::unpack_row(rgba.data(),bgra.data(),0,Layout::argb8));
    assert(!native_rt_readback::unpack_row(rgba.data(),bgra.data(),1,Layout::unsupported));
    assert((bgra==std::array<std::uint8_t,8>{{123,123,123,123,123,123,123,123}}));
}
