#pragma once
// D3D9 signed normal-map texels used by real menu/car/race material samplers.
// The D3D9 LockRect memory layout (U, V, W, Q low-to-high) is the DXGI
// R/G/B/A signed-normalized byte/word order. Do not convert the payload to
// BGRA8 UNORM: doing so changes negative bump directions and material lighting.
// This is CPU-accessible 2D texture data only; unproven GPU RT/cube/sRGB paths
// remain owned by the original D3D9 renderer.
#include <cstdint>
#include <cstring>
#include <limits>

namespace outrun::vr::dx11::live_game_frame::signed_normal_texture {
enum class Layout : std::uint8_t { unsupported, uv8, uvwq8, uv16 };
// D3DFORMAT numeric values from d3d9types.h. Keep this header portable.
[[nodiscard]] constexpr Layout from_d3d9_format(std::uint32_t format) noexcept {
    switch (format) {
    case 60u: return Layout::uv8;   // D3DFMT_V8U8
    case 63u: return Layout::uvwq8; // D3DFMT_Q8W8V8U8
    case 64u: return Layout::uv16;  // D3DFMT_V16U16
    case 62u: return Layout::unsupported; // X8L8V8U8 requires a different L channel
    default: return Layout::unsupported;
    }
}
[[nodiscard]] constexpr std::uint32_t source_bytes_per_texel(Layout l) noexcept {
    switch (l) {
    case Layout::uv8: return 2u;
    case Layout::uvwq8:
    case Layout::uv16: return 4u;
    default: return 0u;
    }
}
[[nodiscard]] constexpr bool sampleable(Layout l, bool srgb) noexcept {
    // D3D11 SNORM SRVs do not expose an sRGB view. Never ignore source
    // D3DSAMP_SRGBTEXTURE when comparing native/game material color.
    return !srgb && source_bytes_per_texel(l) != 0u;
}
[[nodiscard]] constexpr bool row_bytes(std::uint32_t width, Layout l,
                                      std::uint32_t& bytes) noexcept {
    const auto n = source_bytes_per_texel(l);
    if (!width || !n ||
        width > (std::numeric_limits<std::uint32_t>::max)() / n)
        return false;
    bytes = width * n;
    return true;
}
[[nodiscard]] inline bool copy_row(const void* source, void* native,
                                   std::uint32_t width, Layout l) noexcept {
    std::uint32_t bytes{};
    if (!source || !native || !row_bytes(width, l, bytes))
        return false;
    std::memcpy(native, source, bytes);
    return true;
}
static_assert(from_d3d9_format(60u) == Layout::uv8);
static_assert(from_d3d9_format(63u) == Layout::uvwq8);
static_assert(from_d3d9_format(64u) == Layout::uv16);
static_assert(from_d3d9_format(62u) == Layout::unsupported); // X8L8V8U8 is NOT SNORM RGBA
static_assert(!sampleable(Layout::uv8, true));
} // namespace outrun::vr::dx11::live_game_frame::signed_normal_texture