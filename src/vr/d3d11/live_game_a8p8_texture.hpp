#pragma once
#include <cstdint>

// D3D9 A8P8 is (palette index, explicit alpha), not an RGB565 texel.
// Decode using the CURRENT D3D9 palette at the intercepted game Draw;
// the original D3D9 path always remains the authoritative fallback.
namespace outrun::vr::dx11::live_game_frame::a8p8_texture {
struct Rgb {
    std::uint8_t red, green, blue;
};
constexpr unsigned source_bytes_per_texel() noexcept { return 2u; }
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, const Rgb* palette) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        const unsigned in = x * source_bytes_per_texel();
        const unsigned out = x * 4u;
        const Rgb& color = palette[source[in]];
        bgra[out] = color.blue;
        bgra[out + 1u] = color.green;
        bgra[out + 2u] = color.red;
        bgra[out + 3u] = source[in + 1u];
    }
}
} // namespace outrun::vr::dx11::live_game_frame::a8p8_texture
