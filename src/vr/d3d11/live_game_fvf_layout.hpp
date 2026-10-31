#pragma once

#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11::live_game_frame {
// D3D9 FVF constants verified against d3d9types.h by live bridge.
constexpr std::uint32_t kGameFvfXyz = 0x002u;
constexpr std::uint32_t kGameFvfXyzRhw = 0x004u;
constexpr std::uint32_t kGameFvfNormal = 0x010u;
constexpr std::uint32_t kGameFvfPsize = 0x020u;
constexpr std::uint32_t kGameFvfDiffuse = 0x040u;
constexpr std::uint32_t kGameFvfSpecular = 0x080u;
constexpr std::uint32_t kGameFvfTex1 = 0x100u;
constexpr std::uint32_t kGameFvfTex2 = 0x200u;
constexpr std::uint32_t kGameFvfTex3 = 0x300u;
constexpr std::uint32_t kGameFvfTex4 = 0x400u;
constexpr std::uint32_t kGameFvfTex5 = 0x500u;
constexpr std::uint32_t kGameFvfTex6 = 0x600u;
constexpr std::uint32_t kGameFvfTex7 = 0x700u;
constexpr std::uint32_t kGameFvfTex8 = 0x800u;
constexpr std::uint32_t kGameFvfTexCountMask = 0x0f00u;
constexpr std::uint32_t kGameFvfPositionMask = 0x400eu;
// Native 2D sampling reads (u,v) from float1/2/3/4 game FVF streams.
// Untransformed float3/float4 retain original packed offsets; projected
// or transformed higher-dimensional texture coordinates must fail closed.
constexpr std::uint32_t kGameFvfTexcoordSize3_0 = 0x00010000u;
constexpr std::uint32_t kGameFvfTexcoordSize3_7 = 0x40000000u;
constexpr std::uint32_t kGameFvfTexcoordSize4_0 = 0x00020000u;
constexpr std::uint32_t kGameFvfTexcoordSize4_7 = 0x80000000u;
constexpr std::uint32_t game_fvf_texcoord3d_count(std::uint8_t mask) noexcept {
    std::uint32_t count = 0u;
    for (std::uint32_t slot = 0u; slot < 8u; ++slot) count += (mask >> slot) & 1u;
    return count;
}
constexpr std::uint32_t kGameFvfTexcoordSize1_0 = 0x00030000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_1 = 0x000c0000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_2 = 0x00300000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_3 = 0x00c00000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_4 = 0x03000000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_5 = 0x0c000000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_6 = 0x30000000u;
constexpr std::uint32_t kGameFvfTexcoordSize1_7 = 0xc0000000u;
// Real untextured D3D9 menu/vehicle-select FVF DIFFUSE stage semantics.
// COLOROP=DISABLE also disables alpha and all subsequent stages; in enabled
// color operations ALPHAOP=DISABLE is undefined and is never admitted.
constexpr bool game_fvf_untextured_stage0(
    std::uint32_t op, std::uint32_t arg1, std::uint32_t arg2,
    std::uint32_t alphaOp, std::uint32_t alpha1, std::uint32_t alpha2,
    std::uint32_t nextOp, bool diffuse) noexcept {
    if (!diffuse) return false;
    if (op == 1u) return nextOp == 1u;
    const bool rgb = (op == 2u && (arg1 == 0u || arg1 == 1u)) ||
                     (op == 3u && (arg2 == 0u || arg2 == 1u));
    const bool a = (alphaOp == 2u && (alpha1 == 0u || alpha1 == 1u)) ||
                   (alphaOp == 3u && (alpha2 == 0u || alpha2 == 1u));
    return rgb && a;
}
// A TEX1..8 vertex may carry UVs and a stale bound texture even when the
// actual stage-0 combiner uses only vertex DIFFUSE for both RGB and alpha.
// Require the next stage to be disabled: otherwise CURRENT/TEMP or stage-1
// texture operations could still consume the game-owned binding.
constexpr bool game_fvf_diffuse_only_inactive_texture(
    std::uint32_t op, std::uint32_t arg1, std::uint32_t arg2,
    std::uint32_t alphaOp, std::uint32_t alpha1, std::uint32_t alpha2,
    std::uint32_t nextOp, bool diffuse) noexcept {
    return nextOp == 1u &&
        game_fvf_untextured_stage0(op, arg1, arg2, alphaOp, alpha1,
                                   alpha2, nextOp, diffuse);
}
static_assert(game_fvf_diffuse_only_inactive_texture(
    1u, ~0u, ~0u, 4u, ~0u, ~0u, 1u, true));
static_assert(!game_fvf_diffuse_only_inactive_texture(
    2u, 2u, 0u, 2u, 0u, 0u, 1u, true));
static_assert(game_fvf_untextured_stage0(1, ~0u, ~0u, 4, ~0u, ~0u, 1, true));
static_assert(!game_fvf_untextured_stage0(1, 0, 0, 4, 0, 0, 4, true));
struct GameFvfLayout {
    bool pretransformed = false;
    bool textured = false;
    bool hasDiffuse = false;
    bool hasNormal = false;
    bool hasPointSize = false;
    bool hasSpecular = false;
    bool firstTexcoord1D = false;
    bool secondTexcoord1D = false;
    bool thirdTexcoord1D = false;
    bool fourthTexcoord1D = false;
    bool fifthTexcoord1D = false;
    bool sixthTexcoord1D = false;
    bool seventhTexcoord1D = false;
    bool eighthTexcoord1D = false;
    std::uint8_t texcoord3DMask = 0u;
    std::uint8_t texcoord4DMask = 0u;
    std::uint32_t normalBytes = 0;
    std::uint32_t pointSizeBytes = 0;
    std::uint32_t diffuseOffset = 0;
    std::uint32_t texcoordCount = 0;
    std::uint32_t positionBytes = 0;
    std::uint32_t texcoordOffset = 0;
    std::uint32_t minStride = 0;
};
// Omitted DIFFUSE is permitted only for TEX1 SELECTARG1(TEXTURE), not MODULATE.
constexpr bool game_fvf_layout(std::uint32_t fvf, GameFvfLayout& layout) noexcept {
    const std::uint32_t position = fvf & kGameFvfPositionMask;
    const std::uint32_t texcoordBits = fvf & kGameFvfTexCountMask;
    const std::uint32_t firstTexcoordFormat = fvf & kGameFvfTexcoordSize1_0;
    const bool firstTexcoord1D = firstTexcoordFormat == kGameFvfTexcoordSize1_0;
    const std::uint32_t secondTexcoordFormat = fvf & kGameFvfTexcoordSize1_1;
    const bool secondTexcoord1D = secondTexcoordFormat == kGameFvfTexcoordSize1_1;
    const std::uint32_t thirdTexcoordFormat = fvf & kGameFvfTexcoordSize1_2;
    const bool thirdTexcoord1D = thirdTexcoordFormat == kGameFvfTexcoordSize1_2;
    const std::uint32_t fourthTexcoordFormat = fvf & kGameFvfTexcoordSize1_3;
    const bool fourthTexcoord1D = fourthTexcoordFormat == kGameFvfTexcoordSize1_3;
    const std::uint32_t fifthTexcoordFormat = fvf & kGameFvfTexcoordSize1_4;
    const bool fifthTexcoord1D = fifthTexcoordFormat == kGameFvfTexcoordSize1_4;
    const std::uint32_t sixthTexcoordFormat = fvf & kGameFvfTexcoordSize1_5;
    const bool sixthTexcoord1D = sixthTexcoordFormat == kGameFvfTexcoordSize1_5;
    const std::uint32_t seventhTexcoordFormat = fvf & kGameFvfTexcoordSize1_6;
    const bool seventhTexcoord1D = seventhTexcoordFormat == kGameFvfTexcoordSize1_6;
    const std::uint32_t eighthTexcoordFormat = fvf & kGameFvfTexcoordSize1_7;
    const bool eighthTexcoord1D = eighthTexcoordFormat == kGameFvfTexcoordSize1_7;
    // Each declared stage may be float1, float2, float3 or float4.
    // Reject dimension flags for absent stages; malformed
    // game FVFs continue through the original D3D9 Draw.
    std::uint8_t texcoord3DMask = 0u;
    std::uint8_t texcoord4DMask = 0u;
    for (std::uint32_t stage = 0u; stage < 8u; ++stage) {
        const std::uint32_t format = (fvf >> (16u + 2u * stage)) & 3u;
        if (stage >= (texcoordBits >> 8u) && format != 0u)
            return false;
        if (format == 1u)
            texcoord3DMask |= static_cast<std::uint8_t>(1u << stage);
        else if (format == 2u)
            texcoord4DMask |= static_cast<std::uint8_t>(1u << stage);
    }
    // NORMAL and SPECULAR are byte fields preceding texcoords.
    const bool hasNormal = (fvf & kGameFvfNormal) != 0u;
    const bool hasPointSize = (fvf & kGameFvfPsize) != 0u;
    if ((position != kGameFvfXyz && position != kGameFvfXyzRhw) ||
        (position == kGameFvfXyzRhw && hasNormal) ||
        texcoordBits > kGameFvfTex8 ||
        ((firstTexcoordFormat != 0u && !firstTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 0u))) ||
        (firstTexcoord1D && texcoordBits == 0u) ||
        ((secondTexcoordFormat != 0u && !secondTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 1u))) ||
        (secondTexcoord1D && texcoordBits < kGameFvfTex2) ||
        ((thirdTexcoordFormat != 0u && !thirdTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 2u))) ||
        (thirdTexcoord1D && texcoordBits < kGameFvfTex3) ||
        ((fourthTexcoordFormat != 0u && !fourthTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 3u))) ||
        (fourthTexcoord1D && texcoordBits < kGameFvfTex4) ||
        ((fifthTexcoordFormat != 0u && !fifthTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 4u))) ||
        (fifthTexcoord1D && texcoordBits < kGameFvfTex5) ||
        ((sixthTexcoordFormat != 0u && !sixthTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 5u))) ||
        (sixthTexcoord1D && texcoordBits < kGameFvfTex6) ||
        ((seventhTexcoordFormat != 0u && !seventhTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 6u))) ||
        (seventhTexcoord1D && texcoordBits < kGameFvfTex7) ||
        ((eighthTexcoordFormat != 0u && !eighthTexcoord1D) &&
         !((texcoord3DMask | texcoord4DMask) & (1u << 7u))) ||
        (eighthTexcoord1D && texcoordBits < kGameFvfTex8) ||
        (fvf & ~(kGameFvfXyz | kGameFvfXyzRhw | kGameFvfNormal | kGameFvfPsize |
                 kGameFvfDiffuse | kGameFvfSpecular |
                 kGameFvfTexCountMask | kGameFvfTexcoordSize1_0 |
                 kGameFvfTexcoordSize1_1 | kGameFvfTexcoordSize1_2 |
                 kGameFvfTexcoordSize1_3 | kGameFvfTexcoordSize1_4 |
                 kGameFvfTexcoordSize1_5 | kGameFvfTexcoordSize1_6 |
                 kGameFvfTexcoordSize1_7)) != 0u)
        return false;
    GameFvfLayout candidate{};
    candidate.pretransformed = position == kGameFvfXyzRhw;
    candidate.texcoordCount = texcoordBits >> 8u;
    candidate.textured = candidate.texcoordCount != 0u;
    candidate.hasDiffuse = (fvf & kGameFvfDiffuse) != 0u;
    candidate.hasNormal = hasNormal;
    candidate.hasPointSize = hasPointSize;
    candidate.hasSpecular = (fvf & kGameFvfSpecular) != 0u;
    candidate.firstTexcoord1D = firstTexcoord1D;
    candidate.secondTexcoord1D = secondTexcoord1D;
    candidate.thirdTexcoord1D = thirdTexcoord1D;
    candidate.fourthTexcoord1D = fourthTexcoord1D;
    candidate.fifthTexcoord1D = fifthTexcoord1D;
    candidate.sixthTexcoord1D = sixthTexcoord1D;
    candidate.seventhTexcoord1D = seventhTexcoord1D;
    candidate.eighthTexcoord1D = eighthTexcoord1D;
    candidate.texcoord3DMask = texcoord3DMask;
    candidate.texcoord4DMask = texcoord4DMask;
    if (!candidate.textured && !candidate.hasDiffuse) return false;
    candidate.positionBytes = candidate.pretransformed ? 16u : 12u;
    candidate.normalBytes = candidate.hasNormal ? 12u : 0u;
    // FVF stream: POSITION, NORMAL, PSIZE, DIFFUSE, SPECULAR, UVs.
    // Native Draw handles triangles only; ignore the PSIZE value but skip it.
    candidate.pointSizeBytes = candidate.hasPointSize ? 4u : 0u;
    candidate.diffuseOffset = candidate.positionBytes + candidate.normalBytes +
                              candidate.pointSizeBytes;
    candidate.texcoordOffset = candidate.diffuseOffset +
                               (candidate.hasDiffuse ? 4u : 0u) +
                               (candidate.hasSpecular ? 4u : 0u);
    candidate.minStride = candidate.texcoordOffset +
                          candidate.texcoordCount * 8u -
                          (candidate.firstTexcoord1D ? 4u : 0u) -
                          (candidate.secondTexcoord1D ? 4u : 0u) -
                          (candidate.thirdTexcoord1D ? 4u : 0u) -
                          (candidate.fourthTexcoord1D ? 4u : 0u) -
                          (candidate.fifthTexcoord1D ? 4u : 0u) -
                          (candidate.sixthTexcoord1D ? 4u : 0u) -
                          (candidate.seventhTexcoord1D ? 4u : 0u) -
                          (candidate.eighthTexcoord1D ? 4u : 0u) +
                          4u * game_fvf_texcoord3d_count(candidate.texcoord3DMask) +
                          8u * game_fvf_texcoord3d_count(candidate.texcoord4DMask);
    layout = candidate;
    return true;
}
struct GameFvfSample {
    float position[4] = {0.f, 0.f, 0.f, 1.f};
    std::uint32_t diffuse = 0xffffffffu;
    std::uint32_t specular = 0u;
    float uv[2] = {0.f, 0.f};
    float uv1[2] = {0.f, 0.f};
    float uv2[2] = {0.f, 0.f};
    float uv3[2] = {0.f, 0.f};
    float uv4[2] = {0.f, 0.f};
    float uv5[2] = {0.f, 0.f};
    float uv6[2] = {0.f, 0.f};
    float uv7[2] = {0.f, 0.f};
};
// Decode the actual VB/UP slot offsets without reading UV as missing diffuse.
// A bad layout or stride must leave output untouched.
inline bool game_fvf_decode_vertex(const void* bytes, std::uint32_t stride,
                                   const GameFvfLayout& layout,
                                   GameFvfSample& sample) noexcept {
    if (!bytes || (layout.positionBytes != 12u && layout.positionBytes != 16u) ||
        layout.positionBytes != (layout.pretransformed ? 16u : 12u) ||
        (layout.pretransformed && layout.hasNormal) ||
        layout.normalBytes != (layout.hasNormal ? 12u : 0u) ||
        layout.pointSizeBytes != (layout.hasPointSize ? 4u : 0u) ||
        layout.diffuseOffset != layout.positionBytes + layout.normalBytes +
                                layout.pointSizeBytes ||
        layout.texcoordOffset != layout.diffuseOffset +
                                 (layout.hasDiffuse ? 4u : 0u) +
                                 (layout.hasSpecular ? 4u : 0u) ||
        layout.texcoordCount > 8u ||
        (static_cast<std::uint32_t>(layout.texcoord3DMask) >> layout.texcoordCount) != 0u ||
        (static_cast<std::uint32_t>(layout.texcoord4DMask) >> layout.texcoordCount) != 0u ||
        (layout.texcoord3DMask & layout.texcoord4DMask) != 0u ||
        layout.textured != (layout.texcoordCount != 0u) ||
        (layout.firstTexcoord1D && layout.texcoordCount == 0u) ||
        (layout.secondTexcoord1D && layout.texcoordCount < 2u) ||
        (layout.thirdTexcoord1D && layout.texcoordCount < 3u) ||
        (layout.fourthTexcoord1D && layout.texcoordCount < 4u) ||
        (layout.fifthTexcoord1D && layout.texcoordCount < 5u) ||
        (layout.sixthTexcoord1D && layout.texcoordCount < 6u) ||
        (layout.seventhTexcoord1D && layout.texcoordCount < 7u) ||
        (layout.eighthTexcoord1D && layout.texcoordCount < 8u) ||
        layout.minStride != layout.texcoordOffset + layout.texcoordCount * 8u -
                            (layout.firstTexcoord1D ? 4u : 0u) -
                            (layout.secondTexcoord1D ? 4u : 0u) -
                            (layout.thirdTexcoord1D ? 4u : 0u) -
                            (layout.fourthTexcoord1D ? 4u : 0u) -
                            (layout.fifthTexcoord1D ? 4u : 0u) -
                            (layout.sixthTexcoord1D ? 4u : 0u) -
                            (layout.seventhTexcoord1D ? 4u : 0u) -
                            (layout.eighthTexcoord1D ? 4u : 0u) +
                            4u * game_fvf_texcoord3d_count(layout.texcoord3DMask) +
                            8u * game_fvf_texcoord3d_count(layout.texcoord4DMask) ||
        stride < layout.minStride)
        return false;
    GameFvfSample candidate{};
    const auto* data = static_cast<const std::uint8_t*>(bytes);
    std::memcpy(candidate.position, data, layout.positionBytes);
    if (layout.hasDiffuse)
        std::memcpy(&candidate.diffuse, data + layout.diffuseOffset, 4u);
    if (layout.hasSpecular)
        std::memcpy(&candidate.specular, data + layout.diffuseOffset +
            (layout.hasDiffuse ? 4u : 0u), 4u);
    if (layout.texcoordCount >= 1u)
        std::memcpy(candidate.uv, data + layout.texcoordOffset,
                    layout.firstTexcoord1D ? 4u : 8u);
    // Packed U-only UV2..UV7 change subsequent offsets: decode all declared slots
    // sequentially without reading any absent V from the subsequent slot.
    if (layout.thirdTexcoord1D || layout.fourthTexcoord1D ||
        layout.fifthTexcoord1D || layout.sixthTexcoord1D ||
        layout.seventhTexcoord1D || layout.eighthTexcoord1D ||
        layout.texcoord3DMask != 0u || layout.texcoord4DMask != 0u) {
        float* slots[8] = {candidate.uv, candidate.uv1, candidate.uv2, candidate.uv3,
                           candidate.uv4, candidate.uv5, candidate.uv6, candidate.uv7};
        std::uint32_t offset = layout.texcoordOffset;
        for (std::uint32_t slot = 0u; slot < layout.texcoordCount; ++slot) {
            const bool oneDim = (slot == 0u && layout.firstTexcoord1D) ||
                                (slot == 1u && layout.secondTexcoord1D) ||
                                (slot == 2u && layout.thirdTexcoord1D) ||
                                (slot == 3u && layout.fourthTexcoord1D) ||
                                (slot == 4u && layout.fifthTexcoord1D) ||
                                (slot == 5u && layout.sixthTexcoord1D) ||
                                (slot == 6u && layout.seventhTexcoord1D) ||
                                (slot == 7u && layout.eighthTexcoord1D);
            const std::uint32_t bytesToCopy = oneDim ? 4u : 8u;
            std::memcpy(slots[slot], data + offset, bytesToCopy);
            // D3D9 float3/float4 stores trailing coordinates after (u,v).
            // The native untransformed 2D sampler consumes (u,v), while
            // following packed UV stages begin at the original byte offsets.
            if (layout.texcoord4DMask & (1u << slot))
                offset += 16u;
            else if (layout.texcoord3DMask & (1u << slot))
                offset += 12u;
            else
                offset += bytesToCopy;
        }
    // UV1 U-only must not borrow the first float of UV2 as its missing V.
    } else if (layout.secondTexcoord1D) {
        const std::uint32_t secondOffset = layout.texcoordOffset +
                                            (8u - (layout.firstTexcoord1D ? 4u : 0u));
        std::memcpy(candidate.uv1, data + secondOffset, 4u);
        const std::uint32_t later = secondOffset + 4u;
        if (layout.texcoordCount >= 3u)
            std::memcpy(candidate.uv2, data + later, 8u);
        if (layout.texcoordCount >= 4u)
            std::memcpy(candidate.uv3, data + later + 8u, 8u);
        if (layout.texcoordCount >= 5u)
            std::memcpy(candidate.uv4, data + later + 16u, 8u);
        if (layout.texcoordCount >= 6u)
            std::memcpy(candidate.uv5, data + later + 24u, 8u);
        if (layout.texcoordCount >= 7u)
            std::memcpy(candidate.uv6, data + later + 32u, 8u);
        if (layout.texcoordCount >= 8u)
            std::memcpy(candidate.uv7, data + later + 40u, 8u);
    // Missing V defaults to zero; packed later UV sets begin four bytes earlier.
    } else if (layout.firstTexcoord1D) {
        if (layout.texcoordCount >= 2u)
            std::memcpy(candidate.uv1, data + layout.texcoordOffset + 4u, 8u);
        if (layout.texcoordCount >= 3u)
            std::memcpy(candidate.uv2, data + layout.texcoordOffset + 12u, 8u);
        if (layout.texcoordCount >= 4u)
            std::memcpy(candidate.uv3, data + layout.texcoordOffset + 20u, 8u);
        if (layout.texcoordCount >= 5u)
            std::memcpy(candidate.uv4, data + layout.texcoordOffset + 28u, 8u);
        if (layout.texcoordCount >= 6u)
            std::memcpy(candidate.uv5, data + layout.texcoordOffset + 36u, 8u);
        if (layout.texcoordCount >= 7u)
            std::memcpy(candidate.uv6, data + layout.texcoordOffset + 44u, 8u);
        if (layout.texcoordCount >= 8u)
            std::memcpy(candidate.uv7, data + layout.texcoordOffset + 52u, 8u);
    } else {
        if (layout.texcoordCount >= 2u)
            std::memcpy(candidate.uv1, data + layout.texcoordOffset + 8u, 8u);
        if (layout.texcoordCount >= 3u)
            std::memcpy(candidate.uv2, data + layout.texcoordOffset + 16u, 8u);
        if (layout.texcoordCount >= 4u)
            std::memcpy(candidate.uv3, data + layout.texcoordOffset + 24u, 8u);
        if (layout.texcoordCount >= 5u)
            std::memcpy(candidate.uv4, data + layout.texcoordOffset + 32u, 8u);
        if (layout.texcoordCount >= 6u)
            std::memcpy(candidate.uv5, data + layout.texcoordOffset + 40u, 8u);
        if (layout.texcoordCount >= 7u)
            std::memcpy(candidate.uv6, data + layout.texcoordOffset + 48u, 8u);
        if (layout.texcoordCount >= 8u)
            std::memcpy(candidate.uv7, data + layout.texcoordOffset + 56u, 8u);
    }
    sample = candidate;
    return true;
}
// Select the live game stage-0 UV set (0..7); reject absent coordinate slots.
inline bool game_fvf_select_uv(const GameFvfSample& sample,
                               const GameFvfLayout& layout,
                               std::uint32_t coordIndex,
                               float (&uv)[2]) noexcept {
    if (layout.texcoordCount == 0u || layout.texcoordCount > 8u ||
        coordIndex >= layout.texcoordCount)
        return false;
    const float* source = coordIndex == 0u ? sample.uv :
                          coordIndex == 1u ? sample.uv1 :
                          coordIndex == 2u ? sample.uv2 :
                          coordIndex == 3u ? sample.uv3 :
                          coordIndex == 4u ? sample.uv4 :
                          coordIndex == 5u ? sample.uv5 :
                          coordIndex == 6u ? sample.uv6 : sample.uv7;
    std::memcpy(uv, source, sizeof(sample.uv));
    return true;
}
} // namespace outrun::vr::dx11::live_game_frame
