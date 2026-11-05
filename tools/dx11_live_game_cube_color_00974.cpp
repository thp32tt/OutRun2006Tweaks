#include "../src/vr/d3d11/live_game_cube_rt_readback.hpp"
#include <array>
#include <cassert>
#include <cstdint>
namespace cube = outrun::vr::dx11::live_game_frame::cube_rt_readback;
namespace color = outrun::vr::dx11::live_game_frame::native_rt_readback;
using L = color::Layout;
static_assert(cube::sampleable_color(L::argb8, true), "ARGB sRGB");
static_assert(cube::sampleable_color(L::x8b8g8r8, true), "swapped XRGB sRGB");
static_assert(cube::sampleable_color(L::rgb565, false), "packed 16-bit");
static_assert(cube::sampleable_color(L::a2b10g10r10, false), "packed 10-bit");
static_assert(!cube::sampleable_color(L::rgb565, true), "packed sRGB fallback");
static_assert(!cube::sampleable_color(L::a2r10g10b10, true), "10-bit sRGB fallback");
static_assert(!cube::sampleable_color(L::unsupported, false), "unknown fallback");
static_assert(color::source_texel_bytes(L::rgb565) == 2u, "source pitch 16");
static_assert(color::source_texel_bytes(L::argb8) == 4u, "source pitch 32");
static_assert(cube::bounded_six_face_bgra8(512u, 10u), "decoded six-face mip budget");
static_assert(!cube::bounded_six_face_bgra8(1024u, 11u), "full cube limit");
int main() {
    std::array<std::uint8_t, 8> out{};
    const std::array<std::uint8_t, 2> packed565{{0x1fu, 0xf8u}};
    assert(color::unpack_row(packed565.data(), out.data(), 1u, L::rgb565));
    assert(out[0]==255u && out[1]==0u && out[2]==255u && out[3]==255u);
    const std::array<std::uint8_t, 4> swapped{{0x11u,0x22u,0x33u,0x00u}};
    assert(color::unpack_row(swapped.data(), out.data(), 1u, L::x8b8g8r8));
    assert(out[0]==0x33u && out[1]==0x22u && out[2]==0x11u && out[3]==255u);
    const std::array<std::uint8_t, 4> packed10{{0xffu,0x03u,0x00u,0xc0u}};
    assert(color::unpack_row(packed10.data(), out.data(), 1u, L::a2r10g10b10));
    assert(out[0]==255u && out[1]==0u && out[2]==0u && out[3]==255u);
    assert(!color::unpack_row(swapped.data(), out.data(), 1u, L::unsupported));
}
