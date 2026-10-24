#pragma once
// Real D3D9 programmable Draw table Z-fog -> native D3D11 post-PS RGB.
// This is deliberately Z-fog-only: a W-fog capable rasterizer, vertex/range
// fog, sRGB mixing or ambiguous modes cannot publish a guessed GPU frame.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <string>

namespace outrun::vr::dx11 {
struct NativeSm3TableFog {
    std::array<float, 4> rgba{};
    std::array<float, 4> controls{}; // start, end, density, D3DFOGMODE
    bool enabled{};
};
[[nodiscard]] inline bool native_sm3_table_zfog_admission(
    bool fogEnabled, unsigned tableMode, unsigned vertexMode,
    bool rangeFog, bool srgbOutput, bool zFogCapable, bool wFogCapable,
    std::uint32_t color, float start, float end, float density,
    NativeSm3TableFog& result) noexcept {
    result = {};
    if (!fogEnabled) return true; // Native state is unchanged.
    // A real source FOGENABLE can be set with no active equation.
    if (tableMode == 0u && vertexMode == 0u && !rangeFog) return true;
    if (vertexMode != 0u || rangeFog || srgbOutput ||
        !zFogCapable || wFogCapable ||
        (tableMode != 1u && tableMode != 2u && tableMode != 3u) ||
        !std::isfinite(start) || !std::isfinite(end) ||
        !std::isfinite(density) || density < 0.0f ||
        (tableMode == 3u && !(end > start))) return false;
    constexpr float kScale = 1.0f / 255.0f;
    result.rgba = {{
        float((color >> 16u) & 255u) * kScale,
        float((color >> 8u) & 255u) * kScale,
        float(color & 255u) * kScale, 0.0f}};
    result.controls = {{start, end, density, static_cast<float>(tableMode)}};
    result.enabled = true;
    return true;
}
[[nodiscard]] inline float native_sm3_table_zfog_factor(
    unsigned mode, float depth, float start, float end,
    float density) noexcept {
    if (!std::isfinite(depth) || !std::isfinite(start) ||
        !std::isfinite(end) || !std::isfinite(density) ||
        density < 0.0f) return -1.0f;
    const float z = (std::max)(0.0f, depth);
    float factor = -1.0f;
    if (mode == 1u) factor = std::exp(-density * z);
    else if (mode == 2u) factor = std::exp(-density * density * z * z);
    else if (mode == 3u && end > start)
        factor = (end - z) / (end - start);
    return factor < 0.0f ? 0.0f : factor > 1.0f ? 1.0f : factor;
}
[[nodiscard]] inline bool append_native_sm3_table_zfog(
    std::string& shader, bool enabled) {
    if (!enabled) return true;
    const std::string signature =
        "float4 main(R283Input input) : SV_Target0 {";
    const std::string widened =
        "float4 main(R283Input input, float4 r283_fogPosition : SV_Position) : SV_Target0 {";
    const std::string marker = "    return r283_color;\n}\n";
    const auto point = shader.rfind(marker);
    if (point == std::string::npos ||
        point + marker.size() != shader.size() ||
        shader.find(signature) == std::string::npos) return false;
    shader.replace(point, marker.size(),
        "    float r283_z = max(0.0f, r283_fogPosition.z);\n"
        "    float r283_fog = (r283_fogControls.w == 1.0f)\n"
        "        ? exp(-r283_fogControls.z * r283_z)\n"
        "        : ((r283_fogControls.w == 2.0f)\n"
        "            ? exp(-pow(r283_fogControls.z * r283_z, 2.0f))\n"
        "            : (r283_fogControls.y - r283_z) /\n"
        "              (r283_fogControls.y - r283_fogControls.x));\n"
        "    r283_color.rgb = lerp(r283_fogColor.rgb, r283_color.rgb, saturate(r283_fog));\n"
        + marker);
    shader.replace(shader.find(signature), signature.size(), widened);
    shader.insert(0,
        "cbuffer R283TableZFog : register(b4) {\n"
        "    float4 r283_fogColor;\n"
        "    float4 r283_fogControls;\n"
        "};\n");
    return true;
}
} // namespace outrun::vr::dx11
