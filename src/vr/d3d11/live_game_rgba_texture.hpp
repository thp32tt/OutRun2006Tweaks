#pragma once

#include <cstdint>

// D3D9 A8B8G8R8/X8B8G8R8 memory is R,G,B,A/X (little endian).
// The live D3D11 diagnostic SRV is B8G8R8A8, so swap R/B, retaining
// source alpha only for A8B8G8R8. X8 alpha must be opaque on every mip.
namespace outrun::vr::dx11::live_game_frame::rgba_texture {
enum class Layout : std::uint8_t { argb, xrgb };
constexpr unsigned source_bytes_per_texel() noexcept { return 4u; }
constexpr unsigned upload_bytes_per_texel() noexcept { return 4u; }
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        const unsigned offset = 4u * x;
        bgra[offset] = source[offset + 2u];
        bgra[offset + 1u] = source[offset + 1u];
        bgra[offset + 2u] = source[offset];
        bgra[offset + 3u] = layout == Layout::xrgb ? 255u : source[offset + 3u];
    }
}
} // namespace outrun::vr::dx11::live_game_frame::rgba_texture
