#pragma once
#include <cstdint>

// D3D9 R3G3B2 packs RGB in one byte (R:7..5, G:4..2, B:1..0).
// A8R3G3B2 appends an explicit alpha byte in little-endian memory.
// Expand each color field to 8-bit before uploading a BGRA8 D3D11 SRV.
namespace outrun::vr::dx11::live_game_frame::rgb332_texture {
enum class Layout : std::uint8_t { rgb332, a8rgb332 };
constexpr unsigned source_bytes_per_texel(Layout layout) noexcept {
    return layout == Layout::a8rgb332 ? 2u : 1u;
}
constexpr std::uint8_t expand3(std::uint8_t value) noexcept {
    return static_cast<std::uint8_t>((value << 5u) | (value << 2u) | (value >> 1u));
}
constexpr std::uint8_t expand2(std::uint8_t value) noexcept {
    return static_cast<std::uint8_t>((value << 6u) | (value << 4u) | (value << 2u) | value);
}
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    const unsigned stride = source_bytes_per_texel(layout);
    for (unsigned x = 0; x < width; ++x) {
        const unsigned in = x * stride;
        const unsigned out = x * 4u;
        const std::uint8_t color = source[in];
        bgra[out] = expand2(static_cast<std::uint8_t>(color & 0x03u));
        bgra[out + 1u] = expand3(static_cast<std::uint8_t>((color >> 2u) & 0x07u));
        bgra[out + 2u] = expand3(static_cast<std::uint8_t>((color >> 5u) & 0x07u));
        bgra[out + 3u] = layout == Layout::a8rgb332 ? source[in + 1u] : 0xffu;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::rgb332_texture
