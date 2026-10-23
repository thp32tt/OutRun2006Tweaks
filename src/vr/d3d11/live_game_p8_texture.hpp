#pragma once
#include <cstdint>

// D3D9 P8 has a one-byte palette index and no per-texel alpha. On devices
// supporting D3DPTEXTURECAPS_ALPHAPALETTE the live palette supplies alpha;
// otherwise the device samples opaque alpha. Keep both behaviors explicit.
namespace outrun::vr::dx11::live_game_frame::p8_texture {
struct Rgba {
    std::uint8_t red, green, blue, alpha;
};
constexpr unsigned source_bytes_per_texel() noexcept { return 1u; }
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, const Rgba* palette) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        const unsigned out = x * 4u;
        const Rgba& color = palette[source[x]];
        bgra[out] = color.blue;
        bgra[out + 1u] = color.green;
        bgra[out + 2u] = color.red;
        bgra[out + 3u] = color.alpha;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::p8_texture
