#pragma once

#include <cstdint>

// Convert D3D9 A8/L8/A8L8 source texels into the BGRA8 texture format used
// by the live game D3D11 diagnostic renderer. A8 is special: missing RGB=0.
namespace outrun::vr::dx11::live_game_frame::luminance_texture {
enum class Layout : std::uint8_t { alpha8, luminance8, alpha8_luminance8 };

constexpr unsigned source_bytes_per_texel(Layout layout) noexcept {
    return layout == Layout::alpha8_luminance8 ? 2u : 1u;
}

inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    // D3D9 A8L8 source bytes are little-endian: L first, A second.
    switch (layout) {
    case Layout::alpha8:
        for (unsigned x = 0; x < width; ++x) {
            bgra[x * 4u] = 0u;
            bgra[x * 4u + 1u] = 0u;
            bgra[x * 4u + 2u] = 0u;
            bgra[x * 4u + 3u] = source[x];
        }
        break;
    case Layout::luminance8:
        for (unsigned x = 0; x < width; ++x) {
            bgra[x * 4u] = source[x];
            bgra[x * 4u + 1u] = source[x];
            bgra[x * 4u + 2u] = source[x];
            bgra[x * 4u + 3u] = 255u;
        }
        break;
    case Layout::alpha8_luminance8:
        for (unsigned x = 0; x < width; ++x) {
            const auto lum = source[x * 2u];
            bgra[x * 4u] = lum;
            bgra[x * 4u + 1u] = lum;
            bgra[x * 4u + 2u] = lum;
            bgra[x * 4u + 3u] = source[x * 2u + 1u];
        }
        break;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::luminance_texture
