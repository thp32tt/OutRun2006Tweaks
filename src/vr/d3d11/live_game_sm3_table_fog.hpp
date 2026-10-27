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
// The FVF and SM3 game source pipelines share this exact inert-equation test.
// Range fog has no visible contribution when neither equation is enabled.
[[nodiscard]] inline bool native_game_inert_fog_modes(
    unsigned tableMode, unsigned vertexMode) noexcept {
    return tableMode == 0u && vertexMode == 0u; // D3DFOG_NONE
}
// Stable bounded runtime rejection codes: never collapse source state failures
// into an ambiguous "fog" aggregate. Code 12 is reserved for COM query failure.
enum class NativeSm3FogReject : unsigned {
    None = 0u, VertexFog = 1u, RangeFog = 2u, Srgb = 3u,
    MissingZCapability = 4u, WCapability = 5u, TableMode = 6u,
    StartNotFinite = 7u, EndNotFinite = 8u,
    DensityNotFinite = 9u, NegativeDensity = 10u,
    LinearRange = 11u, SourceQuery = 12u
};
[[nodiscard]] inline bool native_sm3_table_zfog_admission(
    bool fogEnabled, unsigned tableMode, unsigned vertexMode,
    bool rangeFog, bool srgbOutput, bool zFogCapable, bool wFogCapable,
    std::uint32_t color, float start, float end, float density,
    NativeSm3TableFog& result,
    NativeSm3FogReject* rejected = nullptr) noexcept {
    result = {};
    if (rejected) *rejected = NativeSm3FogReject::None;
    const auto fail = [&](NativeSm3FogReject cause) noexcept {
        if (rejected) *rejected = cause;
        return false;
    };
    if (!fogEnabled) return true; // The source explicitly disables all fog.
    // RANGEFOGENABLE only changes VERTEX-fog distance calculation. When both
    // actual D3D9 fog equations are NONE it has no influence on source pixels.
    // Do not require a capability, float payload, sRGB mode or inactive
    // range-fog flag for a genuine source no-fog Draw. In particular, this
    // fixes false rejection of live FOGENABLE=1/NONE/NONE/RANGEFOG=1.
    if (native_game_inert_fog_modes(tableMode, vertexMode)) return true;
    // An active equation still needs an exactly mirrored GPU fog pipeline.
    // Preserve conservative Z/W and sRGB restrictions for real fog.
    if (vertexMode != 0u) return fail(NativeSm3FogReject::VertexFog);
    if (rangeFog) return fail(NativeSm3FogReject::RangeFog);
    if (srgbOutput) return fail(NativeSm3FogReject::Srgb);
    if (!zFogCapable) return fail(NativeSm3FogReject::MissingZCapability);
    if (wFogCapable) return fail(NativeSm3FogReject::WCapability);
    if (tableMode != 1u && tableMode != 2u && tableMode != 3u)
        return fail(NativeSm3FogReject::TableMode);
    if (!std::isfinite(start)) return fail(NativeSm3FogReject::StartNotFinite);
    if (!std::isfinite(end)) return fail(NativeSm3FogReject::EndNotFinite);
    if (!std::isfinite(density)) return fail(NativeSm3FogReject::DensityNotFinite);
    if (density < 0.0f) return fail(NativeSm3FogReject::NegativeDensity);
    if (tableMode == 3u && !(end > start))
        return fail(NativeSm3FogReject::LinearRange);
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
