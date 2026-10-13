#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

// D3DFMT_A16B16G16R16 is a little-endian R16,G16,B16,A16 UNORM stream.
// DXGI_FORMAT_R16G16B16A16_UNORM has the same byte/channel layout: unlike
// BGRA8 fallback, copy all 64 bits per texel to preserve game sample precision.
namespace outrun::vr::dx11::live_game_frame::rgba16_texture {
constexpr unsigned source_bytes_per_texel() noexcept { return 8u; }
inline void copy_row(const std::uint8_t* source, std::uint8_t* destination,
                     unsigned width) noexcept {
    std::memcpy(destination, source,
                static_cast<std::size_t>(width) * source_bytes_per_texel());
}
} // namespace outrun::vr::dx11::live_game_frame::rgba16_texture
