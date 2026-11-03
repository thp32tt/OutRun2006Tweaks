#pragma once
#include <cstdint>
// D3D9 G16R16 is little-endian R16 then G16; B=0, alpha=1.
// Mirror readable game mip rows to an opt-in BGRA8 diagnostic SRV.
namespace outrun::vr::dx11::live_game_frame::rg16_texture {
constexpr std::uint8_t expand16(unsigned value) noexcept {
    return static_cast<std::uint8_t>((value * 255u + 32767u) / 65535u);
}
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        const unsigned pos = x * 4u;
        const unsigned red = static_cast<unsigned>(source[pos]) |
            (static_cast<unsigned>(source[pos + 1u]) << 8u);
        const unsigned green = static_cast<unsigned>(source[pos + 2u]) |
            (static_cast<unsigned>(source[pos + 3u]) << 8u);
        bgra[pos] = 0u;
        bgra[pos + 1u] = expand16(green);
        bgra[pos + 2u] = expand16(red);
        bgra[pos + 3u] = 255u;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::rg16_texture
