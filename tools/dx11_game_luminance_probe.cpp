#include "../src/vr/d3d11/live_game_luminance_texture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <algorithm>
using outrun::vr::dx11::live_game_frame::luminance_texture::Layout;
using outrun::vr::dx11::live_game_frame::luminance_texture::source_bytes_per_texel;
using outrun::vr::dx11::live_game_frame::luminance_texture::unpack_row;

int main() {
    static_assert(source_bytes_per_texel(Layout::alpha8) == 1u);
    static_assert(source_bytes_per_texel(Layout::luminance8) == 1u);
    static_assert(source_bytes_per_texel(Layout::alpha8_luminance8) == 2u);
    // Source row padding and partial mips must not contaminate destination.
    const std::array<std::uint8_t, 6> a8{0u, 127u, 255u, 33u, 34u, 35u};
    const std::array<std::uint8_t, 6> l8{0u, 127u, 255u, 33u, 34u, 35u};
    const std::array<std::uint8_t, 8> a8l8{0u, 255u, 127u, 64u, 255u, 0u, 99u, 88u};
    std::array<std::uint8_t, 16> bgra{};
    bgra.fill(0x5a);
    unpack_row(a8.data(), bgra.data(), 3u, Layout::alpha8);
    assert((bgra == std::array<std::uint8_t, 16>{
        0, 0, 0, 0, 0, 0, 0, 127, 0, 0, 0, 255, 0x5a, 0x5a, 0x5a, 0x5a}));
    bgra.fill(0x5a);
    unpack_row(l8.data(), bgra.data(), 3u, Layout::luminance8);
    assert((bgra == std::array<std::uint8_t, 16>{
        0, 0, 0, 255, 127, 127, 127, 255, 255, 255, 255, 255, 0x5a, 0x5a, 0x5a, 0x5a}));
    bgra.fill(0x5a);
    unpack_row(a8l8.data(), bgra.data(), 3u, Layout::alpha8_luminance8);
    assert((bgra == std::array<std::uint8_t, 16>{
        0, 0, 0, 255, 127, 127, 127, 64, 255, 255, 255, 0, 0x5a, 0x5a, 0x5a, 0x5a}));
    for (Layout layout : {Layout::alpha8, Layout::luminance8, Layout::alpha8_luminance8}) {
        bgra.fill(0x5a);
        unpack_row(a8l8.data(), bgra.data(), 1u, layout);
        assert(std::all_of(bgra.begin() + 4, bgra.end(), [](auto v){return v == 0x5a;}));
        bgra.fill(0x5a);
        unpack_row(a8l8.data(), bgra.data(), 0u, layout);
        assert(std::all_of(bgra.begin(), bgra.end(), [](auto v){return v == 0x5a;}));
    }
}
