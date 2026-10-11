#pragma once

#include <cstdint>

// Source D3D9 16-bit texture pixels are little-endian. DX11 diagnostic
// sampling uses BGRA8 so alpha and RGB expansion must preserve D3D9 texels.
// This decoder has no Direct3D dependency and can be CPU-regression tested.
namespace outrun::vr::dx11::live_game_frame::packed_texture16 {
enum class Layout : std::uint8_t { rgb565, argb1555, argb4444 };

struct Bgra8 { std::uint8_t b, g, r, a; };

constexpr std::uint8_t expand4(unsigned value) noexcept {
    return static_cast<std::uint8_t>((value << 4u) | value);
}
constexpr std::uint8_t expand5(unsigned value) noexcept {
    return static_cast<std::uint8_t>((value << 3u) | (value >> 2u));
}
constexpr std::uint8_t expand6(unsigned value) noexcept {
    return static_cast<std::uint8_t>((value << 2u) | (value >> 4u));
}
constexpr Bgra8 unpack(std::uint16_t value, Layout layout) noexcept {
    switch (layout) {
    case Layout::rgb565:
        return {expand5(value & 31u), expand6((value >> 5u) & 63u),
                expand5((value >> 11u) & 31u), 255u};
    case Layout::argb1555:
        return {expand5(value & 31u), expand5((value >> 5u) & 31u),
                expand5((value >> 10u) & 31u),
                static_cast<std::uint8_t>((value & 0x8000u) ? 255u : 0u)};
    case Layout::argb4444:
        return {expand4(value & 15u), expand4((value >> 4u) & 15u),
                expand4((value >> 8u) & 15u), expand4((value >> 12u) & 15u)};
    }
    return {0, 0, 0, 0};
}

inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    for (unsigned x = 0; x < width; ++x) {
        const std::uint16_t texel = static_cast<std::uint16_t>(source[x * 2u]) |
                                    (static_cast<std::uint16_t>(source[x * 2u + 1u]) << 8u);
        const Bgra8 pixel = unpack(texel, layout);
        bgra[x * 4u] = pixel.b;
        bgra[x * 4u + 1u] = pixel.g;
        bgra[x * 4u + 2u] = pixel.r;
        bgra[x * 4u + 3u] = pixel.a;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::packed_texture16
