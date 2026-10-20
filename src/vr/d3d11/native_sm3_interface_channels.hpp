#pragma once

namespace outrun::vr::dx11 {

// SM3 DCL usage ordinals must agree with the live D3D9 declaration -> DX11 IA.
// Only vertex inputs may carry skinning and tangent-basis semantics.
[[nodiscard]] constexpr const char* native_sm3_interface_semantic(
    unsigned usage, bool vertexStage, bool output, unsigned index) noexcept {
    if (index > 15u || (output && !vertexStage)) return nullptr;
    switch (usage) {
    case 0u:
        if (!vertexStage) return nullptr;
        if (output && index != 0u) return nullptr;
        return output ? "SV_Position" : "POSITION";
    case 1u: return vertexStage && !output ? "BLENDWEIGHT" : nullptr;
    case 2u: return vertexStage && !output ? "BLENDINDICES" : nullptr;
    case 3u: return vertexStage ? "NORMAL" : nullptr;
    case 5u: return "TEXCOORD";
    case 6u: return vertexStage && !output ? "TANGENT" : nullptr;
    case 7u: return vertexStage && !output ? "BINORMAL" : nullptr;
    case 10u: return "COLOR";
    default: return nullptr;
    }
}

// Reject any physical source lane that D3D9 did not declare. A native HLSL
// float4 with zero-initialized missing channels is NOT input provenance.
[[nodiscard]] constexpr bool native_sm3_declared_components_cover(
    unsigned declaredMask, unsigned requiredMask) noexcept {
    return declaredMask != 0u && requiredMask != 0u &&
           (declaredMask & ~15u) == 0u &&
           (requiredMask & ~15u) == 0u &&
           (declaredMask & requiredMask) == requiredMask;
}

[[nodiscard]] constexpr bool native_sm3_declared_output_complete(
    unsigned declaredMask, unsigned writtenMask) noexcept {
    return declaredMask != 0u && (declaredMask & ~15u) == 0u &&
           writtenMask == declaredMask;
}

} // namespace outrun::vr::dx11
