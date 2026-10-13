#pragma once
#include "live_game_rgba_texture.hpp"
#include "live_game_10bit_texture.hpp"
#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11::live_game_frame::native_rt_readback {
// D3D9 DEFAULT-pool render targets cannot use Texture::LockRect. After
// GetRenderTargetData snapshots a same-format SYSTEMMEM surface, expand one
// render-target level to an immutable native DX11 BGRA8 sampleable resource.
// This path is diagnostic only; original D3D9 Draw and input still execute.
enum class Layout : std::uint8_t {
    argb8, xrgb8, a8b8g8r8, x8b8g8r8, a2r10g10b10, a2b10g10r10, unsupported
};
constexpr bool sampleable(Layout layout, bool srgb) noexcept {
    return layout != Layout::unsupported &&
           (!srgb || (layout != Layout::a2r10g10b10 &&
                      layout != Layout::a2b10g10r10));
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
    default:
        return false;
    }
}
} // namespace outrun::vr::dx11::live_game_frame::native_rt_readback
