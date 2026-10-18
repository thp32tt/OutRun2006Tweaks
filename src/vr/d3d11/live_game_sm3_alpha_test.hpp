#pragma once

// D3D9 alpha test executes AFTER the programmable pixel shader, against
// ALPHAREF in the 0..255 domain. D3D11 has no fixed-function alpha test:
// generate the actual PS discard before a native menu/race Draw is admitted.
// Mode 0 means disabled; 1..8 match D3DCMP_NEVER..D3DCMP_ALWAYS.
#include <string>

namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_alpha_pass(
    unsigned mode, unsigned alpha, unsigned reference) noexcept {
    if (mode > 8u || alpha > 255u || reference > 255u) return false;
    switch (mode) {
    case 0u: case 8u: return true;
    case 1u: return false;
    case 2u: return alpha < reference;
    case 3u: return alpha == reference;
    case 4u: return alpha <= reference;
    case 5u: return alpha > reference;
    case 6u: return alpha != reference;
    case 7u: return alpha >= reference;
    default: return false;
    }
}

inline bool append_native_sm3_alpha_test(std::string& source,
                                         unsigned mode) {
    if (mode > 8u) return false;
    if (mode == 0u) return true;
    const std::string marker = "    return r283_color;\n}\n";
    const auto point = source.rfind(marker);
    if (point == std::string::npos || point + marker.size() != source.size())
        return false;
    const char* condition = nullptr;
    switch (mode) {
    case 1u: condition = "false"; break;
    case 2u: condition = "r283_alpha < r283_alpha_ref"; break;
    case 3u: condition = "r283_alpha == r283_alpha_ref"; break;
    case 4u: condition = "r283_alpha <= r283_alpha_ref"; break;
    case 5u: condition = "r283_alpha > r283_alpha_ref"; break;
    case 6u: condition = "r283_alpha != r283_alpha_ref"; break;
    case 7u: condition = "r283_alpha >= r283_alpha_ref"; break;
    case 8u: condition = "true"; break;
    default: return false;
    }
    // Alpha is saturated before 8-bit conversion. The D3D9 comparison
    // reference is a raw integer state, not a D3D11 blend constant.
    source.replace(point, marker.size(),
        "    uint r283_alpha = (uint)round(saturate(r283_color.a) * 255.0f);\n"
        "    if (!(" + std::string(condition) + ")) discard;\n"
        + marker);
    source.insert(0,
        "cbuffer R283AlphaTest : register(b1) {\n"
        "    uint r283_alpha_ref; uint3 r283_alpha_pad;\n"
        "};\n");
    return true;
}
} // namespace outrun::vr::dx11
