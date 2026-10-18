#pragma once
// Native SM3 float-register and matrix-op HLSL emission. D3D9 DEF literals
// are shader-owned; unmodified c registers must be supplied by the live
// source device into the corresponding D3D11 VS/PS constant buffer.
#include <array>
#include <cstdint>
#include <string>

namespace outrun::vr::dx11 {
inline bool native_sm3_const_reference(unsigned reg, unsigned limit,
                                      bool defined, std::string& out) {
    if (reg >= limit || reg >= 256u) return false;
    out = defined ? "r283_def" + std::to_string(reg)
                  : "r283_c[" + std::to_string(reg) + "]";
    return true;
}
inline bool append_native_sm3_def(std::string& out, unsigned reg,
                                  const std::array<std::uint32_t, 4>& bits) {
    if (reg >= 256u) return false;
    static constexpr char hex[] = "0123456789abcdef";
    out += "static const float4 r283_def" + std::to_string(reg) + " = float4(";
    for (unsigned i = 0; i < 4u; ++i) {
        if (i) out += ", ";
        out += "asfloat(0x";
        for (int shift = 28; shift >= 0; shift -= 4)
            out += hex[(bits[i] >> shift) & 15u];
        out += "u)";
    }
    out += ");\n";
    return true;
}
inline bool append_native_sm3_matrix(
    std::string& out, const std::string& destination, unsigned mask,
    const std::string& vector,
    const std::array<std::string, 4>& rows,
    unsigned rowCount, unsigned ordinal,
    unsigned vectorComponents = 0u) {
    // Preserve the existing M4x4/M3x3 call signature. For M4x3, M3x4 and
    // M3x2 the physical source vector width differs from output row count.
    if (vectorComponents == 0u)
        vectorComponents = rowCount == 4u ? 4u : 3u;
    const bool supported =
        (vectorComponents == 4u && (rowCount == 4u || rowCount == 3u)) ||
        (vectorComponents == 3u &&
         (rowCount == 4u || rowCount == 3u || rowCount == 2u));
    if (!supported || destination.empty() || vector.empty() ||
        mask == 0u || (mask & ~((1u << rowCount) - 1u)) != 0u)
        return false;
    for (unsigned i = 0; i < rowCount; ++i)
        if (rows[i].empty()) return false;
    const std::string temporary = "r283_matrix_" + std::to_string(ordinal);
    const char* dotLanes = vectorComponents == 4u ? "xyzw" : "xyz";
    static constexpr char kOutputLanes[] = "xyzw";
    out += "    float4 " + temporary + " = float4(";
    for (unsigned i = 0; i < 4u; ++i) {
        if (i) out += ", ";
        if (i < rowCount)
            out += "dot((" + vector + ")." + dotLanes + ", (" +
                   rows[i] + ")." + dotLanes + ")";
        else
            out += "0.0f";
    }
    out += ");\n";
    std::string writeMask;
    for (unsigned i = 0; i < rowCount; ++i)
        if (mask & (1u << i)) writeMask += kOutputLanes[i];
    out += "    " + destination + "." + writeMask +
           " = " + temporary + "." + writeMask + ";\n";
    return true;
}

} // namespace outrun::vr::dx11
