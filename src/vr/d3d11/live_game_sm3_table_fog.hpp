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
// D3D9 selects per-pixel Z or W fog from its *live projection matrix*.
// The fourth column (0,0,0,1) selects device Z. A canonical
// perspective (0,0,1,0) selects eye-relative W when WFOG is supported.
// Arbitrary/noncanonical transforms cannot be guessed by native D3D11.
enum class NativeSm3FogDepth : unsigned { Unknown, Z, W };
[[nodiscard]] inline NativeSm3FogDepth native_sm3_projection_fog_depth(
    float m14, float m24, float m34, float m44,
    bool wFogCapable) noexcept {
    if (!wFogCapable) return NativeSm3FogDepth::Z;
    if (!std::isfinite(m14) || !std::isfinite(m24) ||
        !std::isfinite(m34) || !std::isfinite(m44) ||
        m14 != 0.0f || m24 != 0.0f)
        return NativeSm3FogDepth::Unknown;
    if (m34 == 0.0f && m44 == 1.0f) return NativeSm3FogDepth::Z;
    if (m34 == 1.0f && m44 == 0.0f) return NativeSm3FogDepth::W;
    return NativeSm3FogDepth::Unknown;
}
struct NativeSm3TableFog {
    std::array<float, 4> rgba{}; // RGB fog color, A = exact W-depth selector
    std::array<float, 4> controls{}; // start, end, density, D3DFOGMODE
    bool enabled{};
};
// The FVF and SM3 game source pipelines share this exact inert-equation test.
// Range fog has no visible contribution when neither equation is enabled.
[[nodiscard]] inline bool native_game_inert_fog_modes(
    unsigned tableMode, unsigned vertexMode) noexcept {
    return tableMode == 0u && vertexMode == 0u; // D3DFOG_NONE
}
// D3D9 NONE/NONE equations cannot consume fog float/color/caps state.
// Verify both actual source modes before deciding whether those extra
// getters are necessary. Never infer NONE from a failed mode query.
[[nodiscard]] inline bool native_sm3_fog_needs_parameters(
    bool fogEnabled, unsigned tableMode, unsigned vertexMode) noexcept {
    return fogEnabled && !native_game_inert_fog_modes(tableMode, vertexMode);
}
// D3D9 table fog equations consume disjoint source registers. EXP/EXP2
// use density (not START/END); LINEAR uses START/END (not DENSITY).
// Preserve exact per-Draw COM reads only for the source equation in use.
// Unknown/vertex-only modes never become admitted through this classification.
[[nodiscard]] constexpr bool native_sm3_table_fog_requires_density(
    unsigned tableMode) noexcept {
    return tableMode == 1u || tableMode == 2u; // D3DFOG_EXP/EXP2
}
[[nodiscard]] constexpr bool native_sm3_table_fog_requires_linear_bounds(
    unsigned tableMode) noexcept {
    return tableMode == 3u; // D3DFOG_LINEAR
}
// An active D3D9 EXP/EXP2 table equation with zero density contributes
// exactly 1.0 fog factor for finite raster depth, independently of Z/W
// capability, sRGB, table color and unused start/end. Pixel/table fog
// overrides inherited vertex/range fog. This is NOT a fog-off override:
// demand the actual source table mode and the live density DWORD.
[[nodiscard]] constexpr bool native_sm3_exponential_table_density_probe(
    unsigned tableMode, unsigned vertexMode) noexcept {
    return (tableMode == 1u || tableMode == 2u) && vertexMode <= 3u;
}
[[nodiscard]] inline bool native_sm3_inert_exponential_table_fog(
    unsigned tableMode, unsigned vertexMode, float density) noexcept {
    return native_sm3_exponential_table_density_probe(tableMode, vertexMode) &&
           std::isfinite(density) && density == 0.0f;
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
    NativeSm3FogReject* rejected = nullptr,
    NativeSm3FogDepth sourceDepth = NativeSm3FogDepth::Unknown) noexcept {
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
    // D3D9 pixel/table fog takes priority over any inherited vertex fog.
    // RANGEFOGENABLE changes only vertex-fog distance and has no effect on
    // an active table equation. Still reject invalid vertex mode identities,
    // and never interpret a vertex-only equation as table Z-fog.
    if (vertexMode > 3u || tableMode == 0u)
        return fail(NativeSm3FogReject::VertexFog);
    // A genuine zero-density exponential equation produces the original
    // pixel shader RGB, including on a W-capable device. No fog shader or
    // unused capability/float/color queries may suppress that source Draw.
    if (native_sm3_inert_exponential_table_fog(
            tableMode, vertexMode, density)) return true;
    if (srgbOutput) return fail(NativeSm3FogReject::Srgb);
    // WFOG capability alone does not mean the current source Draw uses W.
    // On a WFOG rasterizer consult the authentic projection matrix before
    // selecting the fog distance. A canonical W projection uses camera Z;
    // an affine projection still uses device Z. Unknown matrices fail closed.
    if (wFogCapable && sourceDepth == NativeSm3FogDepth::Unknown)
        return fail(NativeSm3FogReject::WCapability);
    if (sourceDepth == NativeSm3FogDepth::W && !wFogCapable)
        return fail(NativeSm3FogReject::WCapability);
    if (sourceDepth != NativeSm3FogDepth::W && !zFogCapable)
        return fail(NativeSm3FogReject::MissingZCapability);
    if (tableMode != 1u && tableMode != 2u && tableMode != 3u)
        return fail(NativeSm3FogReject::TableMode);
    // Do not reject a real game Draw because an unused D3D9 fog register
    // is stale, non-finite, or unavailable. Still validate every operand
    // the chosen active equation actually consumes.
    if (native_sm3_table_fog_requires_linear_bounds(tableMode)) {
        if (!std::isfinite(start)) return fail(NativeSm3FogReject::StartNotFinite);
        if (!std::isfinite(end)) return fail(NativeSm3FogReject::EndNotFinite);
        if (!(end > start)) return fail(NativeSm3FogReject::LinearRange);
    } else {
        if (!std::isfinite(density)) return fail(NativeSm3FogReject::DensityNotFinite);
        if (density < 0.0f) return fail(NativeSm3FogReject::NegativeDensity);
    }
    constexpr float kScale = 1.0f / 255.0f;
    result.rgba = {{
        float((color >> 16u) & 255u) * kScale,
        float((color >> 8u) & 255u) * kScale,
        float(color & 255u) * kScale,
        sourceDepth == NativeSm3FogDepth::W ? 1.0f : 0.0f}};
    result.controls = {{start, end, density, static_cast<float>(tableMode)}};
    result.enabled = true;
    return true;
}
[[nodiscard]] inline float native_sm3_table_zfog_factor(
    unsigned mode, float depth, float start, float end,
    float density) noexcept {
    // Match the GPU equation: ignored float operands do not affect the
    // fog factor. This reference is used to compare native RGB semantics.
    if (!std::isfinite(depth)) return -1.0f;
    if (native_sm3_table_fog_requires_linear_bounds(mode)) {
        if (!std::isfinite(start) || !std::isfinite(end) ||
            !(end > start)) return -1.0f;
    } else if (native_sm3_table_fog_requires_density(mode)) {
        if (!std::isfinite(density) || density < 0.0f) return -1.0f;
    } else return -1.0f;
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
        // In PS SV_Position.w is reciprocal homogeneous W, so rcp()\n
        // reconstructs the original eye-relative fog distance only for\n
        // the proven canonical (0,0,1,0) D3D9 projection. Device-space Z\n
        // remains the original path for affine and Z-only rasterizers.\n
        "    float r283_z = max(0.0f, (r283_fogColor.a == 1.0f)\n"
        "        ? rcp(r283_fogPosition.w) : r283_fogPosition.z);\n"
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
