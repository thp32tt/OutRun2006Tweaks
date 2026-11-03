#pragma once

#include <cstdint>

// D3D9 A4L4 and L16 game texels cannot be bound as BGRA8 D3D11 textures.
// Convert each readable mip row without touching D3D9 LockRect padding.
namespace outrun::vr::dx11::live_game_frame::extended_luminance_texture {
enum class Layout : std::uint8_t { alpha4_luminance4, luminance16 };
constexpr unsigned source_bytes_per_texel(Layout layout) noexcept {
    return layout == Layout::luminance16 ? 2u : 1u;
}
constexpr std::uint8_t expand4(unsigned value) noexcept {
    return static_cast<std::uint8_t>(value * 17u);
}
constexpr std::uint8_t expand16(unsigned value) noexcept {
    return static_cast<std::uint8_t>((value * 255u + 32767u) / 65535u);
}
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        std::uint8_t luminance = 0u;
        std::uint8_t alpha = 255u;
        if (layout == Layout::alpha4_luminance4) {
            // A4L4: high nibble alpha, low nibble luminance.
            luminance = expand4(source[x] & 0x0fu);
            alpha = expand4(source[x] >> 4u);
        } else {
            // D3D9 L16 is little endian, normalized to the BGRA8 diagnostic SRV.
            const unsigned offset = x * 2u;
            const unsigned value = static_cast<unsigned>(source[offset]) |
                (static_cast<unsigned>(source[offset + 1u]) << 8u);
            luminance = expand16(value);
        }
        const unsigned offset = x * 4u;
        bgra[offset] = luminance;
        bgra[offset + 1u] = luminance;
        bgra[offset + 2u] = luminance;
        bgra[offset + 3u] = alpha;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::extended_luminance_texture
