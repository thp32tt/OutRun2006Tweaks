#pragma once
// Live programmable D3D9 user clip planes -> native VS SV_ClipDistance.
// D3D9 programmable planes are already expressed in homogeneous clip space.
// This remains diagnostic opt-in; an unproven plane falls back to original D3D9.
#include <array>
#include <cmath>
#include <cstdint>
#include <string>

namespace outrun::vr::dx11 {

struct NativeSm3UserClip {
    std::array<float, 32> constants{}; // plane[6] + enabled[8], VS b4
    bool active{};
};

[[nodiscard]] inline bool native_sm3_user_clip_admission(
    std::uint32_t enabledMask, std::uint32_t devicePlaneCount,
    const std::array<std::array<float, 4>, 6>& source,
    NativeSm3UserClip& out) noexcept {
    out = {};
    if (enabledMask == 0u) return true;
    if (devicePlaneCount > 6u) devicePlaneCount = 6u;
    if (devicePlaneCount == 0u ||
        (enabledMask & ~((1u << devicePlaneCount) - 1u)) != 0u) return false;
    for (unsigned i = 0u; i < 6u; ++i) {
        if ((enabledMask & (1u << i)) == 0u) continue;
        for (unsigned lane = 0u; lane < 4u; ++lane) {
            if (!std::isfinite(source[i][lane])) return false;
            out.constants[i * 4u + lane] = source[i][lane];
        }
        out.constants[24u + i] = 1.0f;
    }
    out.active = true;
    return true;
}

// Inject ONLY into a fully materialized SM3 vertex shader with exact
// SV_Position output. The produced clip distances are tested by the rasterizer;
// absent planes use +1 so they cannot accidentally reject game pixels.
[[nodiscard]] inline bool append_native_sm3_user_clip(
    std::string& shader, bool enabled) {
    if (!enabled) return true;
    constexpr const char* kStruct = "struct R283Output {\n";
    constexpr const char* kPosSemantic = " : SV_Position;\n";
    constexpr const char* kReturn = "    return output;\n}\n";
    const auto structAt = shader.find(kStruct);
    const auto posAt = shader.find(kPosSemantic, structAt);
    const auto returnAt = shader.rfind(kReturn);
    if (structAt == std::string::npos || posAt == std::string::npos ||
        returnAt == std::string::npos ||
        returnAt + std::string(kReturn).size() != shader.size() ||
        shader.find("SV_ClipDistance") != std::string::npos) return false;
    const auto varStart = shader.rfind("    float4 ", posAt);
    if (varStart == std::string::npos || varStart < structAt ||
        posAt <= varStart + 11u) return false;
    const std::string position = shader.substr(
        varStart + 11u, posAt - (varStart + 11u));
    if (position.size() < 2u || position[0] != 'r') return false;
    for (std::size_t i = 1u; i < position.size(); ++i)
        if (position[i] < '0' || position[i] > '9') return false;

    shader.replace(returnAt, std::string(kReturn).size(),
        "    output.r283_clip0 = float4(\n"
        "        lerp(1.0f, dot(output." + position + ", r283_clipPlanes[0]), r283_clipOnA.x),\n"
        "        lerp(1.0f, dot(output." + position + ", r283_clipPlanes[1]), r283_clipOnA.y),\n"
        "        lerp(1.0f, dot(output." + position + ", r283_clipPlanes[2]), r283_clipOnA.z),\n"
        "        lerp(1.0f, dot(output." + position + ", r283_clipPlanes[3]), r283_clipOnA.w));\n"
        "    output.r283_clip1 = float2(\n"
        "        lerp(1.0f, dot(output." + position + ", r283_clipPlanes[4]), r283_clipOnB.x),\n"
        "        lerp(1.0f, dot(output." + position + ", r283_clipPlanes[5]), r283_clipOnB.y));\n"
        + std::string(kReturn));
    shader.insert(structAt + std::string(kStruct).size(),
        "    float4 r283_clip0 : SV_ClipDistance0;\n"
        "    float2 r283_clip1 : SV_ClipDistance1;\n");
    shader.insert(0,
        "cbuffer R283UserClip : register(b4) {\n"
        "    float4 r283_clipPlanes[6];\n"
        "    float4 r283_clipOnA;\n"
        "    float4 r283_clipOnB;\n"
        "};\n");
    return true;
}
} // namespace outrun::vr::dx11
