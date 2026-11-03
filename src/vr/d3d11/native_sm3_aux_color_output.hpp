#pragma once
// Pixel-shader ps_3_0 can write oC1..oC3 while game MRT1..3 are absent
// or explicitly COLORWRITEENABLE-masked. D3D11's sole SV_Target0 must
// still reflect oC0: never alias an auxiliary output to the main RTV.
#include <array>
#include <string>

namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_aux_color_destination(
    bool vertexStage, unsigned registerIndex, unsigned writeMask) noexcept {
    return !vertexStage && registerIndex >= 1u && registerIndex <= 3u &&
           writeMask != 0u && (writeMask & ~15u) == 0u;
}

// Preserve executable SM3 source order, including conditionals and
// destination modifiers. Auxiliary writes live only within the generated
// pixel entrypoint and are discarded by HLSL when native MRT1..3 are inert.
// The live game path MUST independently reject any writable extra RT.
inline void append_native_sm3_ignored_mrt_locals(
    std::string& hlsl, const std::array<bool, 4>& used) {
    for (unsigned slot = 1u; slot < used.size(); ++slot)
        if (used[slot])
            hlsl += "    float4 r283_oC" + std::to_string(slot) +
                    " = float4(0, 0, 0, 0);\n";
}
} // namespace outrun::vr::dx11
