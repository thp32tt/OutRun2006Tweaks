#pragma once
// Native FVF shader source composition. Only game-owned, compiled and
// registered pixel shader entrypoints may request this wrapper. The wrapper
// preserves the original alpha-test/discard and alpha channel; authentic
// table fog operates solely on final RGB before D3D11 OM blending.
#include <string>
#include <string_view>

namespace outrun::vr::dx11 {
[[nodiscard]] inline std::string native_fvf_fog_wrapper(
    std::string_view original) {
    if (original.size() < 2u || original.size() > 96u ||
        original.substr(0u, 2u) != "PS" ||
        original.substr(0u, 13u) == "PSFvfTableFog")
        return {};
    for (const char c : original) {
        if (!((c >= 'A' && c <= 'Z') ||
              (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '_'))
            return {};
    }
    return "float4 PSFvfTableFogVariant(VOut v) : SV_Target {\n"
           "    return FvfApplyTableFog(v, " + std::string(original) + "(v));\n"
           "}\n";
}
// Source D3DSHADE_GOURAUD = 2. FLAT/PHONG/invalid FVF source shading cannot
// use the D3D11 COLOR1 perspective interpolator: preserve D3D9 fallback.
[[nodiscard]] constexpr bool native_fvf_vertex_specular_shade_admitted(
    unsigned shadeMode) noexcept {
    return shadeMode == 2u;
}
// The D3D9 FVF SPECULAR RGB contribution is applied after the texture cascade
// and before output alpha blending, without altering source alpha or discard.
// Caller must have authenticated a live D3DRS_SPECULARENABLE TRUE, FVF COLOR1,
// and absence of active fog. Never generate shader code from an unknown name.
[[nodiscard]] inline std::string native_fvf_specular_wrapper(
    std::string_view original) {
    if (native_fvf_fog_wrapper(original).empty()) return {};
    return "float4 PSFvfSpecularVariant(VOut v) : SV_Target {\n"
           "    float4 color = " + std::string(original) + "(v);\n"
           "    color.rgb = saturate(color.rgb + v.specular.rgb);\n"
           "    return color;\n"
           "}\n";
}
} // namespace outrun::vr::dx11
