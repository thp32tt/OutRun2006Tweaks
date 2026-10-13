#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

// Live D3D9 R16F/G16R16F/R32F/G32R32F LockRect mip rows already carry
// little-endian IEEE754 R[,G] channels expected by native DXGI R/RG FLOAT.
// Preserve negative zero, NaN payloads and signed magnitudes verbatim; no
// artificial B/A expansion or clamped BGRA8 conversion during game Draw*.
namespace outrun::vr::dx11::live_game_frame::float_vector_texture {
enum class Layout : std::uint8_t { r16f, rg16f, r32f, rg32f };
constexpr unsigned source_bytes_per_texel(Layout layout) noexcept {
    switch (layout) {
    case Layout::r16f: return 2u;
    case Layout::rg16f:
    case Layout::r32f: return 4u;
    case Layout::rg32f: return 8u;
    }
    return 0u;
}
inline void copy_row(const std::uint8_t* source, std::uint8_t* destination,
                     unsigned width, Layout layout) noexcept {
    std::memcpy(destination, source,
                static_cast<std::size_t>(width) * source_bytes_per_texel(layout));
}
} // namespace outrun::vr::dx11::live_game_frame::float_vector_texture
