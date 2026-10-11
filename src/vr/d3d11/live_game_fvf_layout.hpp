#pragma once

#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 FVF constants verified against d3d9types.h by live bridge.
constexpr std::uint32_t kGameFvfXyz = 0x002u;
constexpr std::uint32_t kGameFvfXyzRhw = 0x004u;
constexpr std::uint32_t kGameFvfDiffuse = 0x040u;
constexpr std::uint32_t kGameFvfTex1 = 0x100u;
constexpr std::uint32_t kGameFvfTex2 = 0x200u;
constexpr std::uint32_t kGameFvfTex3 = 0x300u;
constexpr std::uint32_t kGameFvfTex4 = 0x400u;
constexpr std::uint32_t kGameFvfTexCountMask = 0x0f00u;
constexpr std::uint32_t kGameFvfPositionMask = 0x400eu;
struct GameFvfLayout {
    bool pretransformed = false;
    bool textured = false;
    bool hasDiffuse = false;
    std::uint32_t texcoordCount = 0;
    std::uint32_t positionBytes = 0;
    std::uint32_t texcoordOffset = 0;
    std::uint32_t minStride = 0;
};
// Omitted DIFFUSE is permitted only for TEX1 SELECTARG1(TEXTURE), not MODULATE.
constexpr bool game_fvf_layout(std::uint32_t fvf, GameFvfLayout& layout) noexcept {
    const std::uint32_t position = fvf & kGameFvfPositionMask;
    const std::uint32_t texcoordBits = fvf & kGameFvfTexCountMask;
    // TEX5+ or non-default coordinate dimensions require a different decoder.
    if ((position != kGameFvfXyz && position != kGameFvfXyzRhw) ||
        texcoordBits > kGameFvfTex4 ||
        (fvf & ~(kGameFvfXyz | kGameFvfXyzRhw |
                 kGameFvfDiffuse | kGameFvfTexCountMask)) != 0u)
        return false;
    GameFvfLayout candidate{};
    candidate.pretransformed = position == kGameFvfXyzRhw;
    candidate.texcoordCount = texcoordBits >> 8u;
    candidate.textured = candidate.texcoordCount != 0u;
    candidate.hasDiffuse = (fvf & kGameFvfDiffuse) != 0u;
    if (!candidate.textured && !candidate.hasDiffuse) return false;
    candidate.positionBytes = candidate.pretransformed ? 16u : 12u;
    candidate.texcoordOffset = candidate.positionBytes +
                               (candidate.hasDiffuse ? 4u : 0u);
    candidate.minStride = candidate.texcoordOffset +
                          candidate.texcoordCount * 8u;
    layout = candidate;
    return true;
}
struct GameFvfSample {
    float position[4] = {0.f, 0.f, 0.f, 1.f};
    std::uint32_t diffuse = 0xffffffffu;
    float uv[2] = {0.f, 0.f};
    float uv1[2] = {0.f, 0.f};
    float uv2[2] = {0.f, 0.f};
    float uv3[2] = {0.f, 0.f};
};
// Decode the actual VB/UP slot offsets without reading UV as missing diffuse.
// A bad layout or stride must leave output untouched.
inline bool game_fvf_decode_vertex(const void* bytes, std::uint32_t stride,
                                   const GameFvfLayout& layout,
                                   GameFvfSample& sample) noexcept {
    if (!bytes || (layout.positionBytes != 12u && layout.positionBytes != 16u) ||
        layout.positionBytes != (layout.pretransformed ? 16u : 12u) ||
        layout.texcoordOffset != layout.positionBytes +
                                 (layout.hasDiffuse ? 4u : 0u) ||
        layout.texcoordCount > 4u ||
        layout.textured != (layout.texcoordCount != 0u) ||
        layout.minStride != layout.texcoordOffset + layout.texcoordCount * 8u ||
        stride < layout.minStride)
        return false;
    GameFvfSample candidate{};
    const auto* data = static_cast<const std::uint8_t*>(bytes);
    std::memcpy(candidate.position, data, layout.positionBytes);
    if (layout.hasDiffuse)
        std::memcpy(&candidate.diffuse, data + layout.positionBytes, 4u);
    if (layout.texcoordCount >= 1u)
        std::memcpy(candidate.uv, data + layout.texcoordOffset, 8u);
    if (layout.texcoordCount >= 2u)
        std::memcpy(candidate.uv1, data + layout.texcoordOffset + 8u, 8u);
    if (layout.texcoordCount >= 3u)
        std::memcpy(candidate.uv2, data + layout.texcoordOffset + 16u, 8u);
    if (layout.texcoordCount >= 4u)
        std::memcpy(candidate.uv3, data + layout.texcoordOffset + 24u, 8u);
    sample = candidate;
    return true;
}
// Select the game stage-0 UV set; reject absent UV1/UV2/UV3.
inline bool game_fvf_select_uv(const GameFvfSample& sample,
                               const GameFvfLayout& layout,
                               std::uint32_t coordIndex,
                               float (&uv)[2]) noexcept {
    if (layout.texcoordCount == 0u || layout.texcoordCount > 4u ||
        coordIndex >= layout.texcoordCount)
        return false;
    const float* source = coordIndex == 0u ? sample.uv :
                          coordIndex == 1u ? sample.uv1 :
                          coordIndex == 2u ? sample.uv2 : sample.uv3;
    std::memcpy(uv, source, sizeof(sample.uv));
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
