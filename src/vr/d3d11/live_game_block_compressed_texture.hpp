#pragma once
// Legacy game block textures: preserve original BC blocks without BGRA quantization.
// DXT2/DXT4 premultiplied alpha uses BC2/BC3; ATI1/ATI2 normals use BC4/BC5.
#include <cstdint>
#include <cstring>
#include <limits>
namespace outrun::vr::dx11::live_game_frame::block_texture {
enum class Layout : std::uint8_t { unsupported, premul_bc2, premul_bc3, bc4, bc5 };
[[nodiscard]] constexpr Layout from_d3d9_format(std::uint32_t format) noexcept {
    switch (format) {
    case 0x32545844u: return Layout::premul_bc2; // DXT2
    case 0x34545844u: return Layout::premul_bc3; // DXT4
    case 0x31495441u: return Layout::bc4; // ATI1
    case 0x32495441u: return Layout::bc5; // ATI2
    default: return Layout::unsupported;
    }
}
[[nodiscard]] constexpr std::uint32_t bytes_per_block(Layout kind) noexcept {
    return kind == Layout::bc4 ? 8u :
        (kind == Layout::premul_bc2 || kind == Layout::premul_bc3 ||
         kind == Layout::bc5) ? 16u : 0u;
}
[[nodiscard]] constexpr bool sampleable(Layout kind, bool srgb) noexcept {
    // Legacy vendor FOURCC sRGB parity has not been established.
    return !srgb && bytes_per_block(kind) != 0u;
}
[[nodiscard]] constexpr bool row_bytes(std::uint32_t width, Layout kind,
                                       std::uint32_t& bytes) noexcept {
    const auto stride = bytes_per_block(kind);
    if (!width || !stride) return false;
    const std::uint64_t blocks = (static_cast<std::uint64_t>(width) + 3u) / 4u;
    const auto size = blocks * stride;
    if (size > (std::numeric_limits<std::uint32_t>::max)()) return false;
    bytes = static_cast<std::uint32_t>(size);
    return true;
}
[[nodiscard]] inline bool copy_row(const void* source, void* destination,
                                   std::uint32_t width, Layout kind) noexcept {
    std::uint32_t bytes{};
    if (!source || !destination || !row_bytes(width, kind, bytes)) return false;
    std::memcpy(destination, source, bytes);
    return true;
}
static_assert(from_d3d9_format(0x32545844u) == Layout::premul_bc2);
static_assert(from_d3d9_format(0x34545844u) == Layout::premul_bc3);
static_assert(from_d3d9_format(0x31495441u) == Layout::bc4);
static_assert(from_d3d9_format(0x32495441u) == Layout::bc5);
static_assert(!sampleable(Layout::bc4, true));
} // namespace outrun::vr::dx11::live_game_frame::block_texture
