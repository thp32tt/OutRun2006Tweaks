#pragma once
#include "live_game_rgba_texture.hpp"
#include "live_game_10bit_texture.hpp"
#include "packed_texture_16bit.hpp"
#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11::live_game_frame::native_rt_readback {
// A mipmapped DEFAULT-pool render target has a distinct GPU surface at each
// mip level. The readback surface must match that level, never the base level.
// D3D9's 1x1 terminal mip is valid even for non-square textures.
[[nodiscard]] constexpr bool matching_mip_extent(
    std::uint32_t baseWidth, std::uint32_t baseHeight,
    std::uint32_t level, std::uint32_t levelWidth,
    std::uint32_t levelHeight) noexcept {
    if (!baseWidth || !baseHeight || !levelWidth || !levelHeight ||
        level >= 32u) return false;
    const auto expectedWidth = baseWidth >> level;
    const auto expectedHeight = baseHeight >> level;
    return levelWidth == (expectedWidth ? expectedWidth : 1u) &&
           levelHeight == (expectedHeight ? expectedHeight : 1u);
}
// D3D9 DEFAULT-pool render targets cannot use Texture::LockRect. After
// GetRenderTargetData snapshots a same-format SYSTEMMEM surface, expand one
// render-target level to an immutable native DX11 BGRA8 sampleable resource.
// This path is diagnostic only; original D3D9 Draw and input still execute.
enum class Layout : std::uint8_t {
    argb8, xrgb8, a8b8g8r8, x8b8g8r8, a2r10g10b10, a2b10g10r10,
    rgb565, argb1555, argb4444, xrgb1555, xrgb4444, unsupported
};
constexpr bool sampleable(Layout layout, bool srgb) noexcept {
    return layout != Layout::unsupported &&
           (!srgb || (layout != Layout::a2r10g10b10 &&
                      layout != Layout::a2b10g10r10 &&
                      layout != Layout::rgb565 &&
                      layout != Layout::argb1555 &&
                      layout != Layout::argb4444 &&
                      layout != Layout::xrgb1555 &&
                      layout != Layout::xrgb4444));
}
inline bool unpack_row(const std::uint8_t* source, std::uint8_t* destination,
                       unsigned width, Layout layout) noexcept {
    if (!source || !destination || !width || layout == Layout::unsupported)
        return false;
    switch (layout) {
    case Layout::argb8:
    case Layout::xrgb8:
        std::memcpy(destination, source, static_cast<std::size_t>(width) * 4u);
        if (layout == Layout::xrgb8)
            for (unsigned x = 0; x < width; ++x) destination[x * 4u + 3u] = 255u;
        return true;
    case Layout::a8b8g8r8:
    case Layout::x8b8g8r8:
        rgba_texture::unpack_row(source, destination, width,
            layout == Layout::x8b8g8r8 ? rgba_texture::Layout::xrgb :
                                         rgba_texture::Layout::argb);
        return true;
    case Layout::a2r10g10b10:
    case Layout::a2b10g10r10:
        tenbit_texture::unpack_row(source, destination, width,
            layout == Layout::a2b10g10r10 ? tenbit_texture::Layout::a2b10g10r10 :
                                           tenbit_texture::Layout::a2r10g10b10);
        return true;
    case Layout::rgb565:
    case Layout::argb1555:
    case Layout::argb4444:
    case Layout::xrgb1555:
    case Layout::xrgb4444: {
        // D3D9 RT16 is staged as SYSTEMMEM then expanded from little-endian
        // pixels to immutable BGRA8 used in real game Draw/DrawIndexed.
        const auto packing = layout == Layout::rgb565 ?
            packed_texture16::Layout::rgb565 :
            layout == Layout::argb1555 ?
            packed_texture16::Layout::argb1555 :
            layout == Layout::argb4444 ?
            packed_texture16::Layout::argb4444 :
            layout == Layout::xrgb1555 ?
            packed_texture16::Layout::xrgb1555 :
            packed_texture16::Layout::xrgb4444;
        packed_texture16::unpack_row(source, destination, width, packing);
        return true;
    }
    default:
        return false;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::native_rt_readback
