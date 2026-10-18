#pragma once
// D3D9 SM3 ps_3_0 TEXLD (ordinary 2D sampling) HLSL emitter.
// Resource slots match original sN; live game tN/sN must be bound by
// the programmable-pipeline owner before this shader can issue a Draw.
#include <string>

namespace outrun::vr::dx11 {

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
    unsigned ordinal) {
    if (destination.empty() || coordinates.empty() ||
        samplerRegister >= 16u || mask == 0u || (mask & ~15u) != 0u)
        return false;
    const auto slot = std::to_string(samplerRegister);
    const auto value = "r283_texel_" + std::to_string(ordinal);
    out += "    float4 " + value + " = r283_texture" + slot +
           ".Sample(r283_sampler" + slot + ", (" +
           coordinates + ").xy);\n";
    static constexpr char kLanes[] = "xyzw";
    std::string lanes;
    for (unsigned i = 0; i < 4u; ++i)
        if ((mask & (1u << i)) != 0u) lanes += kLanes[i];
    out += "    " + destination + "." + lanes + " = " + value + "." +
           lanes + ";\n";
    return true;
}

} // namespace outrun::vr::dx11
