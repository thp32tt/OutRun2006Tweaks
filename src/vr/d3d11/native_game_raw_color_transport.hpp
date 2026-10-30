#pragma once
// Preserve the actual bytes produced by a source-owned D3D11 GPU Draw.
// RGBA8 and BGRA8 render targets have distinct channel ordering; staging
// readback preserves the original (possibly sRGB-encoded) 8-bit RGB values.
// No gamma conversion, synthetic pixels, or full-frame admission is implied.
#include <cstdint>
#include <cstddef>
#include <limits>
#include <initializer_list>
#include "native_game_raw_partial_present_tile.hpp"
#include "native_game_raw_pixel_delta.hpp"
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

 // Transform ONLY the selected source-coincident RGB island. A real game
 // Present may publish four tiny disjoint regions from the same PRE/POST
 // capture; converting all 256x144 pixels for every UpdateSurface repeatedly
 // copies unrelated bytes. D3D9 uses only the exact tile's source RECT.
 // Keep the incomplete magenta edge and all authentic GPU RGB identical.
 [[nodiscard]] inline bool native_raw_copy_present_island(
     void* destination, std::size_t destinationPitch,
     const void* before, std::size_t beforePitch,
     const void* after, std::size_t afterPitch,
     std::uint32_t captureWidth, std::uint32_t captureHeight,
     const NativeRawPresentTile& tile,
     NativeRawColorByteOrder order, bool opaqueXrgb) noexcept {
     if (!destination || !before || !after ||
         !captureWidth || !captureHeight ||
         captureWidth > (std::numeric_limits<std::size_t>::max)() / 4u ||
         tile.copyWidth == 0u || tile.copyHeight == 0u ||
         tile.sourceX >= captureWidth || tile.sourceY >= captureHeight ||
         tile.copyWidth > captureWidth - tile.sourceX ||
         tile.copyHeight > captureHeight - tile.sourceY ||
         destinationPitch < std::size_t{captureWidth} * 4u ||
         beforePitch < std::size_t{captureWidth} * 4u ||
         afterPitch < std::size_t{captureWidth} * 4u)
         return false;
     // The mapped GPU and locked D3D9 pitches must be able to address the
     // last source row without wrapping size_t, including padded row pitches.
     const auto rowBytes = std::size_t{captureWidth} * 4u;
     for (const auto pitch : {destinationPitch, beforePitch, afterPitch})
         if (captureHeight - 1u >
             ((std::numeric_limits<std::size_t>::max)() - rowBytes) / pitch)
             return false;
     const auto* pre = static_cast<const std::uint8_t*>(before);
     const auto* post = static_cast<const std::uint8_t*>(after);
     auto* dst = static_cast<std::uint8_t*>(destination);
     const auto sourceOffset = std::size_t{tile.sourceX} * 4u;
     const auto endX = tile.sourceX + tile.copyWidth;
     const auto endY = tile.sourceY + tile.copyHeight;
     for (auto y = tile.sourceY; y < endY; ++y) {
         const auto* p = pre + std::size_t{y} * beforePitch;
         const auto* a = post + std::size_t{y} * afterPitch;
         auto* d = dst + std::size_t{y} * destinationPitch;
         native_raw_copy_to_d3d9_bgra(
             d + sourceOffset, a + sourceOffset, tile.copyWidth,
             order, opaqueXrgb);
         for (auto x = tile.sourceX; x < endX; ++x) {
             const auto offset = std::size_t{x} * 4u;
             if (native_raw_present_border_pixel(
                     tile, x, y,
                     native_raw_rgb_changed(p + offset, a + offset))) {
                 d[offset] = 255u;
                 d[offset + 1u] = 0u;
                 d[offset + 2u] = 255u;
             }
         }
     }
     return true;
 }
} // namespace outrun::vr::dx11
