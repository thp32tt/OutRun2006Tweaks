#pragma once
// Native SM3 float-register and matrix-op HLSL emission. D3D9 DEF literals
// are shader-owned; unmodified c registers must be supplied by the live
// source device into the corresponding D3D11 VS/PS constant buffer.
#include <array>
#include <cstdint>
#include <string>
#include "native_sm3_address_codegen.hpp"

namespace outrun::vr::dx11 {
inline bool native_sm3_const_reference(unsigned reg, unsigned limit,
                                      bool defined, std::string& out) {
    if (reg >= limit || reg >= 256u) return false;
    out = defined ? "r283_def" + std::to_string(reg)
                  : "r283_c[" + std::to_string(reg) + "]";
    return true;
}
// Shader-owned DEFB overrides the device b# value. An unowned b# is
// sampled on the same real game Draw from Get*ShaderConstantB, never at compile time.
inline bool native_sm3_bool_reference(unsigned reg, bool defined,
                                     std::string& out) {
    if (reg >= 16u) return false;
    out = defined ? "r283_b" + std::to_string(reg)
                  : "(r283_live_b[" + std::to_string(reg) + "].x != 0u)";
    return true;
}
inline void append_native_sm3_live_bool_declaration(std::string& out) {
    out += "cbuffer R283LiveBooleans : register(b2) { uint4 r283_live_b[16]; };\n";
}
inline std::array<std::uint32_t, 64> native_sm3_live_bool_payload(
    const std::array<std::uint32_t, 16>& deviceValues) noexcept {
    std::array<std::uint32_t, 64> packed{};
    for (unsigned reg = 0u; reg < deviceValues.size(); ++reg)
        packed[reg * 4u] = deviceValues[reg] != 0u ? 1u : 0u;
    return packed;
}
inline bool append_native_sm3_defb(std::string& out, unsigned reg,
                                   std::uint32_t literal) {
    if (reg >= 16u || literal > 1u) return false;
    out += "static const bool r283_b" + std::to_string(reg) +
           (literal ? " = true;\n" : " = false;\n");
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


/*
 * Bind an entire game SM3 M*x* c-register matrix, including c[base+a0]
 * and c[base+aL]. Static a0 uses real DEF precedence; aL must refer to
 * an actual bounded D3D9 LOOP and cannot alias shader-local DEF registers.
 * Dynamic i# loops inherit the per-Draw exclusive upper bound, reduced
 * to account for the final matrix row. No partial outputs on rejection.
 */
inline bool native_sm3_relative_matrix_references(
    unsigned base, unsigned rows, unsigned limit,
    bool fromStaticAddress, int staticAddress,
    bool dynamicLoop, int loopMinimum, int loopMaximum, unsigned loopRegister,
    const std::array<bool, 256>& defPresent,
    std::array<std::uint16_t, 16>& loopExclusiveLimits,
    std::array<std::string, 4>& references, bool& readsLive) {
    readsLive = false;
    if (rows < 2u || rows > 4u || limit == 0u || limit > 256u ||
        base >= limit || rows > limit - base ||
        (fromStaticAddress && dynamicLoop))
        return false;
    unsigned dynamicExclusive = 0u;
    if (fromStaticAddress) {
        if (staticAddress < 0 ||
            static_cast<unsigned>(staticAddress) > limit - base - rows)
            return false;
    } else if (dynamicLoop) {
        if (loopRegister >= loopExclusiveLimits.size())
            return false;
        for (unsigned reg = base; reg < limit; ++reg)
            if (defPresent[reg]) return false;
        // aL may address the first row through the last legal matrix.
        // The source Draw validator checks i#.x/y/z against this bound.
        dynamicExclusive = limit - base - rows + 1u;
    } else {
        const auto lowest = static_cast<long long>(base) + loopMinimum;
        const auto highest = static_cast<long long>(base) +
                             static_cast<long long>(rows) - 1 + loopMaximum;
        if (loopMinimum > loopMaximum || lowest < 0 ||
            highest >= static_cast<long long>(limit))
            return false;
        for (auto reg = lowest; reg <= highest; ++reg)
            if (defPresent[static_cast<unsigned>(reg)]) return false;
    }
    std::array<std::string, 4> next{};
    bool live = false;
    for (unsigned row = 0u; row < rows; ++row) {
        if (fromStaticAddress) {
            unsigned index = 0u;
            if (!native_sm3_static_address_const_index(
                    base + row, static_cast<unsigned>(staticAddress),
                    limit, index) ||
                !native_sm3_const_reference(
                    index, limit, defPresent[index], next[row]))
                return false;
            if (!defPresent[index]) live = true;
        } else {
            next[row] = "r283_c[" + std::to_string(base + row) + " + r283_aL]";
            live = true;
        }
    }
    references = std::move(next);
    readsLive = live;
    if (dynamicExclusive) {
        auto& old = loopExclusiveLimits[loopRegister];
        if (!old || dynamicExclusive < old)
            old = static_cast<std::uint16_t>(dynamicExclusive);
    }
    return true;
}

} // namespace outrun::vr::dx11
