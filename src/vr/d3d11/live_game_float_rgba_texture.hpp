#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

// D3D9 A16B16G16R16F and A32B32G32R32F LockRect rows contain
// little-endian R,G,B,A IEEE 754 components, byte-identical to the
// corresponding DXGI FLOAT formats. Do not quantize to BGRA8.
namespace outrun::vr::dx11::live_game_frame::float_rgba_texture {
enum class Layout : std::uint8_t { rgba16f, rgba32f };
constexpr unsigned source_bytes_per_texel(Layout format) noexcept {
    return format == Layout::rgba16f ? 8u : 16u;
}
inline void copy_row(const std::uint8_t* source, std::uint8_t* destination,
                     unsigned width, Layout format) noexcept {
    std::memcpy(destination, source,
                static_cast<std::size_t>(width) * source_bytes_per_texel(format));
}
} // namespace outrun::vr::dx11::live_game_frame::float_rgba_texture
