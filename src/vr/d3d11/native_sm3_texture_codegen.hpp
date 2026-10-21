#pragma once
// D3D9 SM3 ps_3_0 TEXLD (ordinary 2D sampling) HLSL emitter.
// Resource slots match original sN; live game tN/sN must be bound by
// the programmable-pipeline owner before this shader can issue a Draw.
#include <string>

namespace outrun::vr::dx11 {

enum class NativeSm3Texture2DMode {
    Implicit, Projected, Bias, ExplicitLod, Gradients
};

// A D3D9 pixel shader can reach texture operations through IF/ELSE or
// predicate control flow. D3D11 implicit LOD derivatives are not reliable
// there when neighboring pixels take different branches. Explicit LOD and
// explicit gradients are valid: SampleLevel and SampleGrad preserve the
// original game's authored coordinates and derivatives. Unknown modes
// never become native Draw candidates.
[[nodiscard]] constexpr bool native_sm3_texture_mode_allowed_in_control_flow(
    NativeSm3Texture2DMode mode, bool conditional) noexcept {
    switch (mode) {
    case NativeSm3Texture2DMode::Implicit:
    case NativeSm3Texture2DMode::Projected:
    case NativeSm3Texture2DMode::Bias:
        return !conditional;
    case NativeSm3Texture2DMode::ExplicitLod:
    case NativeSm3Texture2DMode::Gradients:
        return true;
    default:
        return false;
    }
}

// The sampler operand is NOT a coordinate vector. Every supported texture
// form reads only the physical lanes it actually consumes; gradients read xy.
[[nodiscard]] constexpr unsigned native_sm3_texture_source_components(
    NativeSm3Texture2DMode mode, unsigned sourceIndex) noexcept {
    if (sourceIndex == 0u)
        return mode == NativeSm3Texture2DMode::Implicit ||
                       mode == NativeSm3Texture2DMode::Gradients ? 0x03u : 0x0bu;
    if (mode == NativeSm3Texture2DMode::Gradients &&
        (sourceIndex == 2u || sourceIndex == 3u))
        return 0x03u;
    return 0u;
}


// TEXLD/TEXLDP/TEXLDB/TEXLDL/TEXLDD coordinates and TEXLDD gradients
// are float source registers. Preserve real D3D9 source modifiers before
// sampling; the caller validates physical TEMP read-mask provenance.
// The sampler sN operand and non-existent gradient operands are not vectors.
// NOT and reserved encodings 13..15 remain on the original D3D9 renderer.
[[nodiscard]] constexpr bool native_sm3_texture_modifier_supported(
    NativeSm3Texture2DMode mode, unsigned sourceIndex,
    unsigned modifier) noexcept {
    if (sourceIndex == 1u)
        return modifier == 0u;
    return native_sm3_texture_source_components(mode, sourceIndex) != 0u &&
           modifier <= 12u;
}

// SM3 cube samplers require XYZ direction and separate face/mip data.
[[nodiscard]] constexpr unsigned native_sm3_cube_source_components(
    NativeSm3Texture2DMode mode, unsigned i) noexcept {
    if (mode == NativeSm3Texture2DMode::Projected) return 0u;
    if (i == 0u) {
        switch (mode) {
        case NativeSm3Texture2DMode::Implicit:
        case NativeSm3Texture2DMode::Gradients: return 0x07u;
        case NativeSm3Texture2DMode::Bias:
        case NativeSm3Texture2DMode::ExplicitLod: return 0x0fu;
        default: return 0u;
        }
    }
    return mode == NativeSm3Texture2DMode::Gradients && (i == 2u || i == 3u)
        ? 0x07u : 0u;
}
[[nodiscard]] constexpr bool native_sm3_cube_modifier_supported(
    NativeSm3Texture2DMode mode, unsigned i, unsigned modifier) noexcept {
    return i == 1u ? modifier == 0u :
        native_sm3_cube_source_components(mode, i) != 0u && modifier <= 12u;
}
inline bool append_native_sm3_texturecube_declarations(
    std::string& out, unsigned samplerRegister) {
    if (samplerRegister >= 16u) return false;
    auto n = std::to_string(samplerRegister);
    out += "TextureCube<float4> r283_texture" + n + " : register(t" + n + ");\n";
    out += "SamplerState r283_sampler" + n + " : register(s" + n + ");\n";
    return true;
}
inline bool append_native_sm3_texturecube_sample(
    std::string& out, const std::string& destination, unsigned mask,
    const std::string& coordinates, unsigned samplerRegister, unsigned ordinal,
    NativeSm3Texture2DMode mode, const std::string& dx,
    const std::string& dy) {
    if (destination.empty() || coordinates.empty() || !mask || (mask & ~15u) ||
        samplerRegister >= 16u ||
        !native_sm3_cube_source_components(mode, 0u) ||
        (mode == NativeSm3Texture2DMode::Gradients
            ? (dx.empty() || dy.empty()) : (!dx.empty() || !dy.empty())))
        return false;
    const auto n = std::to_string(samplerRegister);
    const auto value = "r283_cube_texel_" + std::to_string(ordinal);
    const char* operation = mode == NativeSm3Texture2DMode::Bias ? ".SampleBias(" :
        mode == NativeSm3Texture2DMode::ExplicitLod ? ".SampleLevel(" :
        mode == NativeSm3Texture2DMode::Gradients ? ".SampleGrad(" : ".Sample(";
    out += "    float4 " + value + " = r283_texture" + n +
           operation + "r283_sampler" + n + ", (" + coordinates + ").xyz";
    if (mode == NativeSm3Texture2DMode::Bias ||
        mode == NativeSm3Texture2DMode::ExplicitLod)
        out += ", (" + coordinates + ").w";
    else if (mode == NativeSm3Texture2DMode::Gradients)
        out += ", (" + dx + ").xyz, (" + dy + ").xyz";
    out += ");\n";
    std::string channels;
    for (unsigned i=0; i<4u; ++i)
        if (mask & (1u << i)) channels += "xyzw"[i];
    out += "    " + destination + "." + channels + " = " + value + "." +
           channels + ";\n";
    return true;
}
inline bool append_native_sm3_texture2d_declarations(
    std::string& out, unsigned samplerRegister) {
    if (samplerRegister >= 16u) return false;
    const auto slot = std::to_string(samplerRegister);
    out += "Texture2D<float4> r283_texture" + slot +
           " : register(t" + slot + ");\n";
    out += "SamplerState r283_sampler" + slot +
           " : register(s" + slot + ");\n";
    return true;
}

inline bool append_native_sm3_texture2d_sample(
    std::string& out, const std::string& destination, unsigned mask,
    const std::string& coordinates, unsigned samplerRegister,
    unsigned ordinal, NativeSm3Texture2DMode mode =
                          NativeSm3Texture2DMode::Implicit,
    const std::string& gradientX = {},
    const std::string& gradientY = {}) {
    if (destination.empty() || coordinates.empty() ||
        samplerRegister >= 16u || mask == 0u || (mask & ~15u) != 0u ||
        (mode == NativeSm3Texture2DMode::Gradients
             ? (gradientX.empty() || gradientY.empty())
             : (!gradientX.empty() || !gradientY.empty())))
        return false;
    std::string sampling;
    switch (mode) {
    case NativeSm3Texture2DMode::Implicit:
        sampling = ".Sample("; break;
    case NativeSm3Texture2DMode::Projected:
        sampling = ".Sample("; break;
    case NativeSm3Texture2DMode::Bias:
        sampling = ".SampleBias("; break;
    case NativeSm3Texture2DMode::ExplicitLod:
        sampling = ".SampleLevel("; break;
    case NativeSm3Texture2DMode::Gradients:
        sampling = ".SampleGrad("; break;
    default:
        return false;
    }
    const auto slot = std::to_string(samplerRegister);
    const auto value = "r283_texel_" + std::to_string(ordinal);
    out += "    float4 " + value + " = r283_texture" + slot +
           sampling + "r283_sampler" + slot + ", ";
    if (mode == NativeSm3Texture2DMode::Projected)
        out += "((" + coordinates + ").xy / (" + coordinates + ").w)";
    else
        out += "(" + coordinates + ").xy";
    if (mode == NativeSm3Texture2DMode::Bias ||
        mode == NativeSm3Texture2DMode::ExplicitLod)
        out += ", (" + coordinates + ").w";
    else if (mode == NativeSm3Texture2DMode::Gradients)
        out += ", (" + gradientX + ").xy, (" + gradientY + ").xy";
    out += ");\n";
    static constexpr char kLanes[] = "xyzw";
    std::string lanes;
    for (unsigned i = 0; i < 4u; ++i)
        if ((mask & (1u << i)) != 0u) lanes += kLanes[i];
    out += "    " + destination + "." + lanes + " = " + value + "." +
           lanes + ";\n";
    return true;
}

} // namespace outrun::vr::dx11
