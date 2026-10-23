#pragma once
#include <cstdint>

namespace outrun::vr::dx11 {

// Shared bytecode operand contract for real game-authored D3D9 shaders.
// R266 semantic provenance and the native SM3 HLSL compiler must agree:
// SM3 SINCOS consumes one replicated angle; vertex SGN consumes one
// readable input and two distinct TEMP scratch destinations. The SM2
// SINCOS polynomial coefficients are not interchangeable with SM3.
enum class NativeSm3TrigSignOpcode : std::uint8_t {
    SineCosine,
    Sign,
};

struct NativeSm3TrigSignOperandPlan {
    unsigned sourceCount = 0u;
    bool scratchDestinations = false;
    bool valid = false;
};

[[nodiscard]] constexpr NativeSm3TrigSignOperandPlan
native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode opcode,
    unsigned shaderMajor, bool vertexStage) noexcept {
    if (opcode == NativeSm3TrigSignOpcode::SineCosine) {
        if (shaderMajor == 3u) return {1u, false, true};
        if (shaderMajor == 2u) return {3u, false, true};
    } else if (opcode == NativeSm3TrigSignOpcode::Sign &&
               vertexStage && (shaderMajor == 2u || shaderMajor == 3u)) {
        return {3u, true, true};
    }
    return {};
}
} // namespace outrun::vr::dx11
