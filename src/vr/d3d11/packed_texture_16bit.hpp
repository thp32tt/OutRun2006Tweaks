#pragma once

#include <cstdint>

// Source D3D9 16-bit texture pixels are little-endian. DX11 diagnostic
// sampling uses BGRA8 so alpha and RGB expansion must preserve D3D9 texels.
// This decoder has no Direct3D dependency and can be CPU-regression tested.
namespace outrun::vr::dx11::live_game_frame::packed_texture16 {
enum class Layout : std::uint8_t { rgb565, argb1555, argb4444, xrgb1555, xrgb4444 };

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
    // X1/X4 are unused source bits, never a sampled alpha channel.
    case Layout::xrgb1555:
        return {expand5(value & 31u), expand5((value >> 5u) & 31u),
                expand5((value >> 10u) & 31u), 255u};
    case Layout::xrgb4444:
        return {expand4(value & 15u), expand4((value >> 4u) & 15u),
                expand4((value >> 8u) & 15u), 255u};
    }
    return {0, 0, 0, 0};
}

// Dispatch texture layout once per row, never once per texel. Menu/race
// artwork can contain many sprites; a runtime switch in every sample would
// make the CPU->SRV diagnostic copy needlessly expensive.
template <Layout layout>
inline void unpack_row_typed(const std::uint8_t* source, std::uint8_t* bgra,
                             unsigned width) noexcept {
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
inline void unpack_row(const std::uint8_t* source, std::uint8_t* bgra,
                       unsigned width, Layout layout) noexcept {
    if (layout == Layout::rgb565) {
        unpack_row_typed<Layout::rgb565>(source, bgra, width);
    } else if (layout == Layout::argb1555) {
        unpack_row_typed<Layout::argb1555>(source, bgra, width);
    } else if (layout == Layout::argb4444) {
        unpack_row_typed<Layout::argb4444>(source, bgra, width);
    } else if (layout == Layout::xrgb1555) {
        unpack_row_typed<Layout::xrgb1555>(source, bgra, width);
    } else {
        unpack_row_typed<Layout::xrgb4444>(source, bgra, width);
    }
}
} // namespace outrun::vr::dx11::live_game_frame::packed_texture16
