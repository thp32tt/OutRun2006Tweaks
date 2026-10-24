// Real D3D9 game mip rows -> bit-exact native R/RG FLOAT Draw/Indexed upload.
#include "../src/vr/d3d11/live_game_float_vector_texture.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace f = outrun::vr::dx11::live_game_frame::float_vector_texture;

template<std::size_t N>
bool test_rows(f::Layout layout, const std::array<std::uint8_t, N>& source,
               unsigned width, unsigned rows, std::size_t gamePitch) {
    const std::size_t rowBytes = static_cast<std::size_t>(width) *
                                  f::source_bytes_per_texel(layout);
    if (!rowBytes || gamePitch < rowBytes || gamePitch * rows != N) return false;
    std::array<std::uint8_t, N> native{};
    native.fill(0x5a);
    for (unsigned y = 0; y < rows; ++y)
        f::copy_row(source.data() + y * gamePitch,
                    native.data() + y * rowBytes, width, layout);
    for (unsigned y = 0; y < rows; ++y)
        if (std::memcmp(source.data() + y * gamePitch,
                        native.data() + y * rowBytes, rowBytes) != 0) return false;
    for (std::size_t x = rowBytes * rows; x < N; ++x)
        if (native[x] != 0x5a) return false;
    return true;
}
int main() {
    static_assert(f::source_bytes_per_texel(f::Layout::r16f) == 2);
    static_assert(f::source_bytes_per_texel(f::Layout::rg16f) == 4);
    static_assert(f::source_bytes_per_texel(f::Layout::r32f) == 4);
    static_assert(f::source_bytes_per_texel(f::Layout::rg32f) == 8);
    // Two padded game rows: 0x8000 is -0 half, 0x7e01 carries half NaN
    // payload, 0x7c00 half INF. Every native row must exclude poison pitch.
    constexpr std::array<std::uint8_t,16> r16{{
        0x00,0x80, 0x01,0x7e, 0xee,0xee,0xee,0xee,
        0x00,0x3c, 0x00,0x7c, 0xdd,0xdd,0xdd,0xdd}};
    constexpr std::array<std::uint8_t,24> rg16{{
        0x00,0x3c, 0x00,0x80, 0x01,0x7e, 0x00,0x7c, 0xee,0xee,0xee,0xee,
        0x00,0xbc, 0x00,0x40, 0x00,0x00, 0x00,0x38, 0xdd,0xdd,0xdd,0xdd}};
    constexpr std::array<std::uint8_t,24> r32{{
        0x00,0x00,0x00,0x80, 0x01,0x00,0xc0,0x7f, 0xee,0xee,0xee,0xee,
        0x00,0x00,0x80,0x3f, 0x00,0x00,0x80,0x7f, 0xdd,0xdd,0xdd,0xdd}};
    constexpr std::array<std::uint8_t,40> rg32{{
        0x00,0x00,0x80,0x3f, 0x00,0x00,0x00,0x80,
        0x01,0x00,0xc0,0x7f, 0x00,0x00,0x00,0x00,
        0xee,0xee,0xee,0xee,
        0x00,0x00,0x80,0xbf, 0x00,0x00,0x00,0x3f,
        0x00,0x00,0x80,0x7f, 0x00,0x00,0x00,0x00,
        0xdd,0xdd,0xdd,0xdd}};
    if (!test_rows(f::Layout::r16f, r16, 2, 2, 8) ||
        !test_rows(f::Layout::rg16f, rg16, 2, 2, 12) ||
        !test_rows(f::Layout::r32f, r32, 2, 2, 12) ||
        !test_rows(f::Layout::rg32f, rg32, 2, 2, 20)) return 1;
    // The next 1x1 mip has a distinct pitch and stays exact.
    constexpr std::array<std::uint8_t,8> mip{{0x00,0x3c,0x00,0x80,
                                              0x01,0x7e,0x00,0x7c}};
    std::array<std::uint8_t,8> native{};
    f::copy_row(mip.data(), native.data(), 1, f::Layout::rg32f);
    if (native != mip) return 2;
    std::puts("00693 PASS: R/RG 16F/32F bit-exact LockRect rows, padded pitches, mip payload");
    return 0;
}
