// 00661: source D3D9 X1R5G5B5/X4R4G4B4 texels -> BGRA8 live native Draw.
#include "../src/vr/d3d11/packed_texture_16bit.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::packed_texture16;
static_assert(unpack(0x7c00u, Layout::xrgb1555).r == 255u);
static_assert(unpack(0x7c00u, Layout::xrgb1555).a == 255u);
static_assert(unpack(0xfc00u, Layout::xrgb1555).a == 255u);
static_assert(unpack(0x0f00u, Layout::xrgb4444).r == 255u);
static_assert(unpack(0x0f00u, Layout::xrgb4444).a == 255u);
static_assert(unpack(0xff00u, Layout::xrgb4444).a == 255u);
static_assert(unpack(0x7c00u, Layout::argb1555).a == 0u);
static_assert(unpack(0x0f00u, Layout::argb4444).a == 0u);
int main() {
    // Each of two D3D9 LockRect rows has 2 bytes padding; never copy it.
    const std::array<std::uint8_t, 12> source{0x00,0x7c,0x1f,0x00,0xaa,0xbb,
                                               0xe0,0x03,0x00,0xfc,0xcc,0xdd};
    std::array<std::uint8_t, 20> bgra{};
    bgra.fill(19u);
    for (unsigned y = 0; y < 2u; ++y)
        unpack_row(source.data()+y*6u, bgra.data()+y*8u, 2u, Layout::xrgb1555);
    assert((bgra == std::array<std::uint8_t, 20>{
        0,0,255,255, 255,0,0,255,
        0,255,0,255, 0,0,255,255, 19,19,19,19
    }));
    // The 1x1 mip must not take alpha from X4's high nibble.
    const std::array<std::uint8_t, 6> mip{0xf0,0xff,0xde,0xad,0xbe,0xef};
    bgra.fill(19u);
    unpack_row(mip.data(), bgra.data(), 1u, Layout::xrgb4444);
    assert((std::array<std::uint8_t, 4>{bgra[0],bgra[1],bgra[2],bgra[3]} ==
            std::array<std::uint8_t, 4>{0,255,255,255}));
    const std::array<std::uint8_t, 2> clearTop{0x00,0x0f};
    unpack_row(clearTop.data(), bgra.data(), 1u, Layout::xrgb4444);
    assert((std::array<std::uint8_t, 4>{bgra[0],bgra[1],bgra[2],bgra[3]} ==
            std::array<std::uint8_t, 4>{0,0,255,255}));
    bgra.fill(19u);
    unpack_row(mip.data(), bgra.data(), 0u, Layout::xrgb1555);
    for (auto b : bgra) assert(b == 19u);
}
