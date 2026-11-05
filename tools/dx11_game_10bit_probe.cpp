// 00662: live A2R10G10B10/A2B10G10R10 game mips -> BGRA8 native Draw.
#include "../src/vr/d3d11/live_game_10bit_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame::tenbit_texture;
static_assert(unpack(0xfff00000u, Layout::a2r10g10b10).r == 255u);
static_assert(unpack(0xfff00000u, Layout::a2r10g10b10).b == 0u);
static_assert(unpack(0xc00003ffu, Layout::a2r10g10b10).b == 255u);
static_assert(unpack(0xc00003ffu, Layout::a2b10g10r10).r == 255u);
static_assert(unpack(0xfff00000u, Layout::a2b10g10r10).b == 255u);
static_assert(unpack(0x000ffc00u, Layout::a2r10g10b10).a == 0u);
static_assert(unpack(0x40000000u, Layout::a2b10g10r10).a == 85u);
static_assert(expand10(512u) == 128u);
int main() {
    // Two D3D9 LockRect rows, each with four poisoned padding bytes.
    constexpr std::array<std::uint8_t, 24> source{
        0x00,0x00,0xf0,0xff, 0xff,0x03,0x00,0xc0, 0xaa,0xbb,0xcc,0xdd,
        0x00,0xfc,0x0f,0x00, 0x00,0x00,0x00,0x40, 0xde,0xad,0xbe,0xef};
    std::array<std::uint8_t, 20> destination{};
    destination.fill(19u);
    for (unsigned y = 0; y < 2u; ++y)
        unpack_row(source.data() + y * 12u, destination.data() + y * 8u,
                   2u, Layout::a2r10g10b10);
    assert((destination == std::array<std::uint8_t, 20>{
        0,0,255,255, 255,0,0,255,
        0,255,0,0, 0,0,0,85, 19,19,19,19}));
    const std::array<std::uint8_t, 8> mip{0xff,0x03,0x00,0xc0, 0x11,0x22,0x33,0x44};
    destination.fill(19u);
    unpack_row(mip.data(), destination.data(), 1u, Layout::a2b10g10r10);
    assert((std::array<std::uint8_t, 4>{destination[0],destination[1],destination[2],destination[3]} ==
            std::array<std::uint8_t, 4>{0,0,255,255}));
    for (unsigned i = 4; i < destination.size(); ++i) assert(destination[i] == 19u);
    unpack_row(mip.data(), destination.data(), 0u, Layout::a2r10g10b10);
    assert(destination[0] == 0u && destination[2] == 255u);
}
