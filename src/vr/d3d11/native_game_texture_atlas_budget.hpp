#pragma once
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
// Conservative per-Draw staging budget for game-authored 2K menu/car atlases.
// It bounds the *converted* native mip payload, not the smaller D3D9 source
// palette/packed payload. The source D3D9 Draw/input always run on rejection.
inline constexpr std::uint32_t kMaxNativeGameAtlasDimension = 2048u;
inline constexpr std::uint64_t kMaxNativeGameAtlasUploadBytes = 24ull * 1024ull * 1024ull;

// A compressed texture supplies exactly one BC block byte width (8/16),
// whereas an uncompressed texture supplies its D3D11 texel byte width.
// Returns zero for unsupported dimensions, excessive allocation or metadata.
[[nodiscard]] constexpr std::uint64_t native_game_texture_upload_bytes(
    std::uint32_t width, std::uint32_t height, std::uint32_t levels,
    std::uint32_t nativeTexelBytes, std::uint32_t blockBytes) noexcept {
    if (!width || !height || !levels || levels > 12u ||
        width > kMaxNativeGameAtlasDimension ||
        height > kMaxNativeGameAtlasDimension ||
        ((blockBytes != 0u) == (nativeTexelBytes != 0u)) ||
        (blockBytes && blockBytes != 8u && blockBytes != 16u) ||
        (nativeTexelBytes && nativeTexelBytes != 4u &&
         nativeTexelBytes != 8u && nativeTexelBytes != 16u))
        return 0u;
    std::uint64_t total = 0u;
    for (std::uint32_t level = 0; level < levels; ++level) {
        const std::uint64_t w = (width >> level) ? (width >> level) : 1u;
        const std::uint64_t h = (height >> level) ? (height >> level) : 1u;
        const std::uint64_t bytes = blockBytes ?
            ((w + 3u) / 4u) * ((h + 3u) / 4u) * blockBytes :
            w * h * nativeTexelBytes;
        if (bytes > kMaxNativeGameAtlasUploadBytes - total)
            return 0u;
        total += bytes;
    }
    return total;
}
} // namespace outrun::vr::dx11::live_game_frame
