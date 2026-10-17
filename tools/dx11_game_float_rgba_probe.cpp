// Game-authored float RGBA LockRect -> format-preserving native SRV mip rows.
#include "../src/vr/d3d11/live_game_float_rgba_texture.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace t = outrun::vr::dx11::live_game_frame::float_rgba_texture;
int main() {
    static_assert(t::source_bytes_per_texel(t::Layout::rgba16f) == 8u);
    static_assert(t::source_bytes_per_texel(t::Layout::rgba32f) == 16u);
    // Two half-float texels, 8 bytes each, plus 8 poison pitch-padding bytes.
    // Values include signed -0, +inf, and NaN payload: preserve raw bits.
    constexpr std::array<std::uint8_t, 48> game16{{
        0x00,0x3c, 0x00,0x80, 0x00,0x7c, 0x01,0x7e,
        0x00,0x00, 0x00,0x38, 0x00,0x40, 0x00,0xbc,
        0xee,0xee,0xee,0xee,0xee,0xee,0xee,0xee,
        0x00,0x34, 0x00,0x3a, 0x00,0x3e, 0x00,0x42,
        0x00,0x44, 0x00,0x46, 0x00,0x48, 0x00,0x4a,
        0xdd,0xdd,0xdd,0xdd,0xdd,0xdd,0xdd,0xdd
    }};
    std::array<std::uint8_t, 32> upload16{};
    t::copy_row(game16.data(), upload16.data(), 2, t::Layout::rgba16f);
    t::copy_row(game16.data()+24, upload16.data()+16, 2, t::Layout::rgba16f);
    if (std::memcmp(game16.data(), upload16.data(), 16) != 0 ||
        std::memcmp(game16.data()+24, upload16.data()+16, 16) != 0 ||
        upload16[7] != 0x7e || upload16[31] != 0x4a) return 1;
    // 32-bit floating RGBA, including signed zero and fractional payload.
    constexpr std::array<std::uint8_t, 40> game32{{
        0x00,0x00,0x80,0x3f, 0x00,0x00,0x00,0x80,
        0x00,0x00,0x00,0x3e, 0x00,0x00,0x80,0x7f,
        0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,
        0x00,0x00,0x00,0xbf, 0x00,0x00,0x80,0x3e,
        0x00,0x00,0xc0,0x7f, 0x00,0x00,0x00,0x00
    }};
    std::array<std::uint8_t, 32> upload32{};
    t::copy_row(game32.data(), upload32.data(), 1, t::Layout::rgba32f);
    t::copy_row(game32.data()+24, upload32.data()+16, 1, t::Layout::rgba32f);
    if (std::memcmp(game32.data(), upload32.data(), 16) != 0 ||
        std::memcmp(game32.data()+24, upload32.data()+16, 16) != 0 ||
        upload32[27] != 0x7f) return 2;
    // Every mip level must use its own native pitch, not the padded game pitch.
    constexpr std::array<std::uint8_t, 8> halfMip{{0x00,0x3c,0x00,0x38,0x00,0x34,0x00,0x3c}};
    std::array<std::uint8_t, 8> nativeMip{};
    t::copy_row(halfMip.data(), nativeMip.data(), 1, t::Layout::rgba16f);
    if (nativeMip != halfMip) return 3;
    std::puts("00670 PASS: float RGBA16F/RGBA32F mip rows preserve channel bits and skip LockRect padding");
}
