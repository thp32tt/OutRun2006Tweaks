// Offline, host-independent texel conversion probe for DX11 live game draws.
#include "../src/vr/d3d11/packed_texture_16bit.hpp"
#include <cassert>
#include <cstdint>
#include <array>

using namespace outrun::vr::dx11::live_game_frame::packed_texture16;
static_assert(unpack(0xf800u, Layout::rgb565).r == 255u);
static_assert(unpack(0x07e0u, Layout::rgb565).g == 255u);
static_assert(unpack(0x001fu, Layout::rgb565).b == 255u);
static_assert(unpack(0x7c00u, Layout::argb1555).a == 0u);
static_assert(unpack(0xfc00u, Layout::argb1555).a == 255u);
static_assert(unpack(0x8421u, Layout::argb4444).a == 136u);

int main() {
    // Pad the source pitch deliberately: only two source bytes per texel.
    const std::array<std::uint8_t, 8> row{0x00, 0xf8, 0xe0, 0x07, 0xaa, 0xbb, 0xcc, 0xdd};
    std::array<std::uint8_t, 8> dest{};
    unpack_row(row.data(), dest.data(), 2, Layout::rgb565);
    assert((dest == std::array<std::uint8_t, 8>{0, 0, 255, 255, 0, 255, 0, 255}));
    // The same 16-bit payload is interpreted differently by each D3D format.
    auto p = unpack(0x0f01u, Layout::argb4444);
    assert(p.b == 17 && p.g == 0 && p.r == 255 && p.a == 0);
    auto q = unpack(0x8000u, Layout::argb1555);
    assert(q.a == 255 && q.r == 0 && q.g == 0 && q.b == 0);
    std::array<std::uint8_t, 4> argb1555{};
    const std::array<std::uint8_t, 2> transparentRed{0x00, 0x7c};
    unpack_row(transparentRed.data(), argb1555.data(), 1, Layout::argb1555);
    assert((argb1555 == std::array<std::uint8_t, 4>{0, 0, 255, 0}));
    std::array<std::uint8_t, 4> argb4444{};
    const std::array<std::uint8_t, 2> translucentRed{0x00, 0x8f};
    unpack_row(translucentRed.data(), argb4444.data(), 1, Layout::argb4444);
    assert((argb4444 == std::array<std::uint8_t, 4>{0, 0, 255, 136}));
    return 0;
}
