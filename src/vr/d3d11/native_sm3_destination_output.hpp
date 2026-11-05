#pragma once
// Translate D3D9 SM3 destination shift and saturation on native GPU output.
// Every supported transform executes after the actual VS/PS instruction,
// inside any existing predicate or dynamic flow block. No channel widening.
#include <string>

namespace outrun::vr::dx11 {

[[nodiscard]] constexpr bool native_sm3_destination_modifiers_accepted(
    unsigned modifier, unsigned shift) noexcept {
    // Only _sat is an exact modifier in this translation. Partial precision,
    // centroid and reserved bits cannot be silently discarded.
    if (modifier > 1u) return false;
    // D3D9 shifts use a signed 4-bit exponent. Bound the supported PS range
    // to +/-3 and fail closed on reserved or larger variants.
    return shift <= 3u || shift == 13u || shift == 14u || shift == 15u;
}

inline bool append_native_sm3_destination_postprocess(
    std::string& hlsl, const std::string& destination, unsigned mask,
    unsigned modifier, unsigned shift) {
    if (destination.empty() || mask == 0u || (mask & ~15u) != 0u ||
        !native_sm3_destination_modifiers_accepted(modifier, shift))
        return false;
    if (modifier == 0u && shift == 0u) return true;

    std::string lanes;
    constexpr char xyzw[] = "xyzw";
    for (unsigned i = 0; i != 4u; ++i)
        if ((mask & (1u << i)) != 0u) lanes += xyzw[i];
    const std::string target = destination + "." + lanes;
    std::string expression = target;
    const char* scale = nullptr;
    switch (shift) {
    case 0u: break;
    case 1u: scale = "2.0f"; break;
    case 2u: scale = "4.0f"; break;
    case 3u: scale = "8.0f"; break;
    case 13u: scale = "0.125f"; break;
    case 14u: scale = "0.25f"; break;
    case 15u: scale = "0.5f"; break;
    default: return false;
    }
    if (scale)
        expression = "(" + expression + " * " + scale + ")";
    if (modifier == 1u)
        expression = "saturate(" + expression + ")";
    hlsl += "    " + target + " = " + expression + ";\n";
    return true;
}

} // namespace outrun::vr::dx11
