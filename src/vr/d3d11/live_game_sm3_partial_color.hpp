#pragma once
// Real D3D9 SM3 oC0 register lanes and RT0 COLORWRITEENABLE are independent.
// Shader HLSL may initialize missing lanes for definite assignment only when
// source OM prevents those lanes from becoming visible GPU pixels.
// The game's original Draw, input and FFB remain authoritative on rejection.
namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_partial_color_draw_allowed(
    unsigned sourceColorMask, unsigned shaderWrittenMask,
    bool shaderWritesDepth, bool alphaTest) noexcept {
    if ((sourceColorMask & ~15u) != 0u ||
        (shaderWrittenMask & ~15u) != 0u) return false;
    if (!shaderWrittenMask)
        return shaderWritesDepth && !sourceColorMask && !alphaTest;
    if ((sourceColorMask & ~shaderWrittenMask) != 0u) return false;
    // D3D9 alpha testing consumes the authored PS alpha even when RT0 alpha
    // is masked. Do not compare HLSL's uninitialized placeholder.
    if (alphaTest && (shaderWrittenMask & 8u) == 0u) return false;
    return sourceColorMask != 0u || shaderWritesDepth;
}
} // namespace outrun::vr::dx11
