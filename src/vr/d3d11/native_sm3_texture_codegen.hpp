#pragma once
// D3D9 SM3 ps_3_0 TEXLD (ordinary 2D sampling) HLSL emitter.
// Resource slots match original sN; live game tN/sN must be bound by
// the programmable-pipeline owner before this shader can issue a Draw.
#include <string>

namespace outrun::vr::dx11 {

enum class NativeSm3Texture2DMode {
    Implicit, Projected, Bias, ExplicitLod, Gradients
};

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
