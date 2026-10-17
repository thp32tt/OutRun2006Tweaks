// 00663: real game A4L4/L16 LockRect bytes -> DX11 BGRA8 mip upload.
#include "../src/vr/d3d11/live_game_extended_luminance_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::extended_luminance_texture;
static_assert(source_bytes_per_texel(Layout::alpha4_luminance4) == 1u);
static_assert(source_bytes_per_texel(Layout::luminance16) == 2u);
static_assert(expand4(0u) == 0u && expand4(8u) == 136u && expand4(15u) == 255u);
static_assert(expand16(0u) == 0u && expand16(32768u) == 128u && expand16(65535u) == 255u);
int main() {
    constexpr std::array<std::uint8_t, 8> a4l4{
        0x0f, 0xf0, 0xaa, 0xbb,
        0x87, 0x38, 0xcc, 0xdd};
    std::array<std::uint8_t, 20> result{};
    result.fill(19u);
    for (unsigned y = 0u; y < 2u; ++y)
        unpack_row(a4l4.data() + y * 4u, result.data() + y * 8u,
                   2u, Layout::alpha4_luminance4);
    assert((result == std::array<std::uint8_t, 20>{
        255,255,255,0, 0,0,0,255,
        119,119,119,136, 136,136,136,51, 19,19,19,19}));

    constexpr std::array<std::uint8_t, 12> l16{
        0x00,0x00, 0xff,0xff, 0xaa,0xbb,
        0x00,0x80, 0x01,0x00, 0xcc,0xdd};
    result.fill(19u);
    for (unsigned y = 0u; y < 2u; ++y)
        unpack_row(l16.data() + y * 6u, result.data() + y * 8u,
                   2u, Layout::luminance16);
    assert((result == std::array<std::uint8_t, 20>{
        0,0,0,255, 255,255,255,255,
        128,128,128,255, 0,0,0,255, 19,19,19,19}));

    // 1x1 final mip must ignore extra source padding, and zero width is a no-op.
    constexpr std::array<std::uint8_t, 6> mip{0xff,0x7f,0xee,0xdd,0xcc,0xbb};
    result.fill(19u);
    unpack_row(mip.data(), result.data(), 1u, Layout::luminance16);
    assert((std::array<std::uint8_t, 4>{result[0],result[1],result[2],result[3]} ==
            std::array<std::uint8_t, 4>{127,127,127,255}));
    for (unsigned i = 4u; i < result.size(); ++i) assert(result[i] == 19u);
    unpack_row(mip.data(), result.data(), 0u, Layout::alpha4_luminance4);
    assert(result[0] == 127u && result[3] == 255u);
}
