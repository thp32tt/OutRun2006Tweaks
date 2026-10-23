#pragma once

#include <cstdint>

// Game-created D3D9 10:10:10:2 texels are not BGRA8 byte-compatible.
// Read little-endian bytes without unaligned/aliasing casts and expand each mip
// into a sampleable native D3D11 BGRA8 SRV.
namespace outrun::vr::dx11::live_game_frame::tenbit_texture {
enum class Layout : std::uint8_t { a2r10g10b10, a2b10g10r10 };
struct Bgra8 { std::uint8_t b, g, r, a; };
constexpr std::uint8_t expand10(unsigned channel) noexcept {
    return static_cast<std::uint8_t>((channel * 255u + 511u) / 1023u);
}
constexpr Bgra8 unpack(std::uint32_t packed, Layout layout) noexcept {
    const unsigned low = packed & 1023u;
    const unsigned green = (packed >> 10u) & 1023u;
    const unsigned high = (packed >> 20u) & 1023u;
    const std::uint8_t alpha = static_cast<std::uint8_t>(((packed >> 30u) & 3u) * 85u);
    return layout == Layout::a2r10g10b10 ?
        Bgra8{expand10(low), expand10(green), expand10(high), alpha} :
        Bgra8{expand10(high), expand10(green), expand10(low), alpha};
}
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        const unsigned off = x * 4u;
        const std::uint32_t packed = static_cast<std::uint32_t>(source[off]) |
            (static_cast<std::uint32_t>(source[off + 1u]) << 8u) |
            (static_cast<std::uint32_t>(source[off + 2u]) << 16u) |
            (static_cast<std::uint32_t>(source[off + 3u]) << 24u);
        const Bgra8 rgba = unpack(packed, layout);
        bgra[off] = rgba.b;
        bgra[off + 1u] = rgba.g;
        bgra[off + 2u] = rgba.r;
        bgra[off + 3u] = rgba.a;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::tenbit_texture
