#pragma once
// Game-owned D3D9 volume rows -> DXGI Texture3D texels. Pure/portable
// conversion; no guessed GPU-only data or precision-destroying float casts.
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace outrun::vr::dx11::live_game_frame::live_volume {
enum class PixelLayout { unsupported, bgra8, bgrx8, rgba8, rgbx8, r16f, rgba16f };
[[nodiscard]] constexpr unsigned bytes_per_texel(PixelLayout layout) noexcept {
    switch (layout) {
    case PixelLayout::bgra8: case PixelLayout::bgrx8:
    case PixelLayout::rgba8: case PixelLayout::rgbx8: return 4u;
    case PixelLayout::r16f: return 2u;
    case PixelLayout::rgba16f: return 8u;
    default: return 0u;
    }
}
[[nodiscard]] inline bool convert_row(const std::uint8_t* source,
    std::uint8_t* destination, std::uint32_t width, PixelLayout layout) noexcept {
    const auto size = bytes_per_texel(layout);
    if (!source || !destination || !width || !size) return false;
    if (layout == PixelLayout::rgba8 || layout == PixelLayout::r16f ||
        layout == PixelLayout::rgba16f) {
        std::memcpy(destination, source, static_cast<std::size_t>(width) * size);
        return true;
    }
    for (std::uint32_t x = 0; x < width; ++x) {
        const auto* p = source + 4u * x;
        auto* d = destination + 4u * x;
        d[0] = layout == PixelLayout::bgra8 || layout == PixelLayout::bgrx8 ? p[2] : p[0];
        d[1] = p[1];
        d[2] = layout == PixelLayout::bgra8 || layout == PixelLayout::bgrx8 ? p[0] : p[2];
        d[3] = layout == PixelLayout::bgrx8 || layout == PixelLayout::rgbx8 ? 255u : p[3];
    }
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame::live_volume
