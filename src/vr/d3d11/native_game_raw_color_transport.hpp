#pragma once
// Preserve the actual bytes produced by a source-owned D3D11 GPU Draw.
// RGBA8 and BGRA8 render targets have distinct channel ordering; staging
// readback preserves the original (possibly sRGB-encoded) 8-bit RGB values.
// No gamma conversion, synthetic pixels, or full-frame admission is implied.
#include <cstdint>
#include <cstddef>
namespace outrun::vr::dx11 {
enum class NativeRawColorByteOrder : std::uint8_t { Bgra, Rgba };
inline void native_raw_copy_to_d3d9_bgra(
    std::uint8_t* dst, const std::uint8_t* source,
    std::uint32_t pixels, NativeRawColorByteOrder order,
    bool opaqueXrgb) noexcept {
    for (std::uint32_t x = 0u; x < pixels; ++x) {
        const auto i = static_cast<std::size_t>(x) * 4u;
        if (order == NativeRawColorByteOrder::Rgba) {
            dst[i] = source[i + 2u];
            dst[i + 1u] = source[i + 1u];
            dst[i + 2u] = source[i];
        } else {
            dst[i] = source[i];
            dst[i + 1u] = source[i + 1u];
            dst[i + 2u] = source[i + 2u];
        }
        dst[i + 3u] = opaqueXrgb ? 255u : source[i + 3u];
    }
}
} // namespace outrun::vr::dx11
